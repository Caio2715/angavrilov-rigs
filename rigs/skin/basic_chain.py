#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

import bpy

from itertools import count, repeat
from mathutils import Vector, Matrix

from rigify.utils.rig import connected_children_names
from rigify.utils.layers import ControlLayersOption
from rigify.utils.naming import make_derived_name
from rigify.utils.bones import align_bone_orientation, align_bone_to_axis, align_bone_roll
from rigify.utils.widgets_basic import create_cube_widget, create_sphere_widget
from rigify.utils.misc import map_list

from rigify.base_rig import stage

from .skin_rigs import BaseSkinChainRigWithRotationOption, ControlBoneNode


def compute_chain_orientation(obj, bone_names):
    """
    Compute the orientation matrix with x axis perpendicular
    to the primary plane in which the bones lie.
    """
    pb = obj.pose.bones
    first_bone = pb[bone_names[0]]
    last_bone = pb[bone_names[-1]]

    y_axis = last_bone.tail - first_bone.head

    if y_axis.length < 1e-4:
        y_axis = (last_bone.head - first_bone.tail).normalized()
    else:
        y_axis.normalize()

    x_axis = first_bone.y_axis.normalized().cross(y_axis)

    if x_axis.length < 1e-4:
        z_axis = first_bone.x_axis.cross(y_axis).normalized()

        return Matrix((y_axis.cross(z_axis), y_axis, z_axis)).transposed()
    else:
        x_axis.normalize()

        return Matrix((x_axis, y_axis, x_axis.cross(y_axis))).transposed()


class Rig(BaseSkinChainRigWithRotationOption):
    """Skin chain with completely independent control nodes."""

    def find_org_bones(self, bone):
        return [bone.name] + connected_children_names(self.obj, bone.name)

    def initialize(self):
        super().initialize()

        self.bbone_segments = self.params.bbones

        orgs = self.bones.org

        self.num_orgs = len(orgs)
        self.length = sum([self.get_bone(b).length for b in orgs]) / len(orgs)
        self.chain_rot = compute_chain_orientation(self.obj, orgs).to_quaternion()

    def get_control_node_rotation(self):
        return self.chain_rot

    ####################################################
    # CONTROL NODES

    @stage.initialize
    def init_control_nodes(self):
        orgs = self.bones.org

        self.control_nodes = nodes = [
            # Bone head nodes
            *map_list(self.make_control_node, count(0), orgs, repeat(False)),
            # Tail of the final bone
            self.make_control_node(len(orgs), orgs[-1], True),
        ]

        nodes[0].chain_neigbor = nodes[1]
        nodes[-1].chain_neigbor = nodes[-2]

    def make_control_node(self, i, org, is_end):
        bone = self.get_bone(org)
        name = make_derived_name(org, 'ctrl', '_end' if is_end else '')
        pos = bone.tail if is_end else bone.head
        return ControlBoneNode(self, org, name, point=pos, size=self.length/2, index=i)

    def make_control_node_widget(self, node):
        create_sphere_widget(self.obj, node.control_bone)

    ####################################################
    # BONES
    #
    # mch:
    #   handles[]
    #     B-Bone handles.
    # deform[]:
    #   Deformation B-Bones.
    #
    ####################################################

    ####################################################
    # B-Bone handle MCH

    def get_node_chain_with_mirror(self):
        nodes = self.control_nodes
        prev_mirror_node = nodes[0].get_best_mirror()
        next_mirror_node = nodes[-1].get_best_mirror()
        return [
            prev_mirror_node.chain_neigbor if prev_mirror_node else None,
            *nodes,
            next_mirror_node.chain_neigbor if next_mirror_node else None,
        ]

    @stage.generate_bones
    def make_mch_handle_bones(self):
        chain = self.get_node_chain_with_mirror()

        self.bones.mch.handles = map_list(self.make_mch_handle_bone, count(0), chain, chain[1:], chain[2:])

    def make_mch_handle_bone(self, i, prev_node, node, next_node):
        name = self.copy_bone(node.org, make_derived_name(node.name, 'mch', '_handle'))

        hstart = prev_node or node
        hend = next_node or node
        haxis = (hend.point - hstart.point).normalized()

        bone = self.get_bone(name)
        bone.head = hstart.point
        bone.tail = hstart.point + haxis * self.length * 3/4

        align_bone_roll(self.obj, name, node.org)
        return name

    @stage.parent_bones
    def parent_mch_handle_bones(self):
        for mch in self.bones.mch.handles:
            self.set_bone_parent(mch, self.rig_parent_bone, inherit_scale='AVERAGE')

    @stage.rig_bones
    def rig_mch_handle_bones(self):
        mch = self.bones.mch
        chain = self.get_node_chain_with_mirror()

        for args in zip(count(0), mch.handles, chain, chain[1:], chain[2:]):
            self.rig_mch_handle_bone(*args)

    def rig_mch_handle_bone(self, i, mch, prev_node, node, next_node):
        hstart = prev_node or node
        hend = next_node or node

        # Emulate auto handle
        self.make_constraint(mch, 'COPY_LOCATION', hstart.control_bone)
        self.make_constraint(mch, 'DAMPED_TRACK', hend.control_bone)

        # Apply user rotation and scale
        self.make_constraint(
            mch, 'COPY_TRANSFORMS', node.control_bone,
            target_space='OWNER_LOCAL', owner_space='LOCAL',
            mix_mode='BEFORE_FULL',
        )

        # Remove any shear created by previous step
        self.make_constraint(mch, 'LIMIT_ROTATION')


    ##############################
    # ORG chain

    @stage.parent_bones
    def parent_org_chain(self):
        pass

    @stage.rig_bones
    def rig_org_chain(self):
        for args in zip(count(0), self.bones.org, self.control_nodes, self.control_nodes[1:]):
            self.rig_org_bone(*args)

    def rig_org_bone(self, i, org, node, next_node):
        if i == 0:
            self.make_constraint(org, 'COPY_LOCATION', node.control_bone)

        self.make_constraint(org, 'STRETCH_TO', next_node.control_bone, keep_axis='SWING_Y')


    ##############################
    # Deform chain

    @stage.generate_bones
    def make_deform_chain(self):
        self.bones.deform = map_list(self.make_deform_bone, count(0), self.bones.org)

    def make_deform_bone(self, i, org):
        name = self.copy_bone(org, make_derived_name(org, 'def'), bbone=True)
        self.get_bone(name).bbone_segments = self.bbone_segments
        return name

    @stage.parent_bones
    def parent_deform_chain(self):
        deform = self.bones.deform

        self.set_bone_parent(deform[0], self.rig_parent_bone, inherit_scale='AVERAGE')
        self.parent_bone_chain(deform, use_connect=True, inherit_scale='AVERAGE')

        handles = self.bones.mch.handles

        for name, start_handle, end_handle in zip(deform, handles, handles[1:]):
            bone = self.get_bone(name)
            bone.bbone_handle_type_start = 'TANGENT'
            bone.bbone_custom_handle_start = self.get_bone(start_handle)
            bone.bbone_handle_type_end = 'TANGENT'
            bone.bbone_custom_handle_end = self.get_bone(end_handle)

    @stage.rig_bones
    def rig_deform_chain(self):
        for args in zip(count(0), self.bones.deform, self.bones.org):
            self.rig_deform_bone(*args)

    def rig_deform_bone(self, i, deform, org):
        self.make_constraint(deform, 'COPY_TRANSFORMS', org)


    ####################################################
    # SETTINGS

    @classmethod
    def add_parameters(self, params):
        params.bbones = bpy.props.IntProperty(
            name        = 'B-Bone Segments',
            default     = 10,
            min         = 1,
            description = 'Number of B-Bone segments'
        )

        super().add_parameters(params)

    @classmethod
    def parameters_ui(self, layout, params):
        r = layout.row()
        r.prop(params, "bbones")

        super().parameters_ui(layout, params)