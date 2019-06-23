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

from rigify.utils.errors import MetarigError
from rigify.utils.rig import connected_children_names
from rigify.utils.layers import ControlLayersOption
from rigify.utils.bones import BoneUtilityMixin, flip_bone

from rigify.base_generate import SubstitutionRig

from .basic_spine import Rig as BasicSpineRig
from .basic_tail import Rig as BasicTailRig
from .super_head import Rig as SuperHeadRig


class Rig(SubstitutionRig, BoneUtilityMixin):
    """Compatibility proxy for the monolithic super_spine rig that splits it into parts."""

    def substitute(self):
        params_copy = dict(self.params)
        orgs = [self.base_bone] + connected_children_names(self.obj, self.base_bone)

        # Split the bone list according to the settings
        spine_orgs = orgs
        head_orgs = None
        tail_orgs = None

        pivot_pos = self.params.pivot_pos

        if self.params.use_head:
            neck_pos = self.params.neck_pos
            if neck_pos <= pivot_pos:
                raise MetarigError("RIGIFY ERROR: Neck cannot be below or the same as pivot.")
            if neck_pos >= len(orgs):
                raise MetarigError("RIGIFY ERROR: Neck is too short.")

            spine_orgs = orgs[0 : neck_pos-1]
            head_orgs = orgs[neck_pos-1 : ]

        if self.params.use_tail:
            tail_pos = self.params.tail_pos
            if tail_pos < 2:
                raise MetarigError("RIGIFY ERROR: Tail is too short.")
            if tail_pos >= pivot_pos:
                raise MetarigError("RIGIFY ERROR: Tail cannot be above or the same as pivot.")

            tail_orgs = list(reversed(spine_orgs[0 : tail_pos]))
            spine_orgs = spine_orgs[tail_pos : ]
            pivot_pos -= tail_pos

        # Split the bone chain and flip the tail
        if head_orgs or tail_orgs:
            bpy.ops.object.mode_set(mode='EDIT')

            if spine_orgs[0] != orgs[0]:
                self.set_bone_parent(spine_orgs[0], self.get_bone_parent(orgs[0]))

            if head_orgs:
                self.get_bone(head_orgs[0]).use_connect = False

            if tail_orgs:
                for org in tail_orgs:
                    self.set_bone_parent(org, None)

                for org in tail_orgs:
                    flip_bone(self.obj, org)

                self.set_bone_parent(tail_orgs[0], spine_orgs[0])
                self.parent_bone_chain(tail_orgs, use_connect=True)

            bpy.ops.object.mode_set(mode='OBJECT')

        # Create the parts
        self.assign_params(spine_orgs[0], params_copy, pivot_pos=pivot_pos)

        result = [ self.instantiate_rig(BasicSpineRig, spine_orgs[0]) ]

        if tail_orgs:
            self.assign_params(tail_orgs[0], params_copy, connect_chain=True)

            result += [ self.instantiate_rig(BasicTailRig, tail_orgs[0]) ]

        if head_orgs:
            self.assign_params(head_orgs[0], params_copy, connect_chain=True)

            result += [ self.instantiate_rig(SuperHeadRig, head_orgs[0]) ]

        return result


def add_parameters(params):
    BasicSpineRig.add_parameters(params)
    BasicTailRig.add_parameters(params)
    SuperHeadRig.add_parameters(params)

    params.neck_pos = bpy.props.IntProperty(
        name        = 'neck_position',
        default     = 6,
        min         = 0,
        description = 'Neck start position'
    )

    params.tail_pos = bpy.props.IntProperty(
        name='tail_position',
        default=2,
        min=2,
        description='Where the tail starts'
    )

    params.use_tail = bpy.props.BoolProperty(
        name='use_tail',
        default=False,
        description='Create tail bones'
    )

    params.use_head = bpy.props.BoolProperty(
        name='use_head',
        default=True,
        description='Create head and neck bones'
    )


def parameters_ui(layout, params):
    """ Create the ui for the rig parameters."""

    r = layout.row(align=True)
    r.prop(params, "use_head", toggle=True, text="Head")
    r.prop(params, "use_tail", toggle=True, text="Tail")

    r = layout.row()
    r.prop(params, "neck_pos")
    r.enabled = params.use_head

    r = layout.row()
    r.prop(params, "pivot_pos")

    r = layout.row()
    r.prop(params, "tail_pos")
    r.enabled = params.use_tail

    r = layout.row()
    col = r.column(align=True)
    row = col.row(align=True)
    for i, axis in enumerate(['x', 'y', 'z']):
        row.prop(params, "copy_rotation_axes", index=i, toggle=True, text=axis)
    r.enabled = params.use_tail

    ControlLayersOption.TWEAK.parameters_ui(layout, params)


def create_sample(obj):
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('spine')
    bone.head[:] = 0.0000, 0.0552, 1.0099
    bone.tail[:] = 0.0000, 0.0172, 1.1573
    bone.roll = 0.0000
    bone.use_connect = False
    bones['spine'] = bone.name

    bone = arm.edit_bones.new('spine.001')
    bone.head[:] = 0.0000, 0.0172, 1.1573
    bone.tail[:] = 0.0000, 0.0004, 1.2929
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine']]
    bones['spine.001'] = bone.name

    bone = arm.edit_bones.new('spine.002')
    bone.head[:] = 0.0000, 0.0004, 1.2929
    bone.tail[:] = 0.0000, 0.0059, 1.4657
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.001']]
    bones['spine.002'] = bone.name

    bone = arm.edit_bones.new('spine.003')
    bone.head[:] = 0.0000, 0.0059, 1.4657
    bone.tail[:] = 0.0000, 0.0114, 1.6582
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.002']]
    bones['spine.003'] = bone.name

    bone = arm.edit_bones.new('spine.004')
    bone.head[:] = 0.0000, 0.0114, 1.6582
    bone.tail[:] = 0.0000, -0.013, 1.7197
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.003']]
    bones['spine.004'] = bone.name

    bone = arm.edit_bones.new('spine.005')
    bone.head[:] = 0.0000, -0.013, 1.7197
    bone.tail[:] = 0.0000, -0.0247, 1.7813
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.004']]
    bones['spine.005'] = bone.name

    bone = arm.edit_bones.new('spine.006')
    bone.head[:] = 0.0000, -0.0247, 1.7813
    bone.tail[:] = 0.0000, -0.0247, 1.9796
    bone.roll = 0.0000
    bone.use_connect = True
    bone.parent = arm.edit_bones[bones['spine.005']]
    bones['spine.006'] = bone.name


    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['spine']]
    pbone.rigify_type = 'spines.super_spine'
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'

    try:
        pbone.rigify_parameters.neck_pos = 5
    except AttributeError:
        pass
    try:
        pbone.rigify_parameters.tweak_layers = [False, False, False, False, True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    except AttributeError:
        pass
    pbone = obj.pose.bones[bones['spine.001']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.002']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.003']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.004']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.005']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    pbone = obj.pose.bones[bones['spine.006']]
    pbone.rigify_type = ''
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
    for b in bones:
        bone = arm.edit_bones[bones[b]]
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        arm.edit_bones.active = bone