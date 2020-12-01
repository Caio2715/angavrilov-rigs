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
import collections
import heapq
import operator

from mathutils import Vector, Quaternion
from mathutils.kdtree import KDTree

from rigify.utils.errors import MetarigError
from rigify.base_rig import stage, GenerateCallbackHost
from rigify.base_generate import GeneratorPlugin


class NodeMerger(GeneratorPlugin):
    """Utility to partition nodes into groups based on their location, with epsilon."""

    epsilon = 1e-5

    def __init__(self, generator, domain):
        super().__init__(generator)

        assert domain is not None
        assert generator.stage == 'initialize'

        self.domain = domain
        self.nodes = []
        self.final_nodes = []
        self.groups = []
        self.frozen = False

    def register_node(self, node):
        assert not self.frozen
        self.nodes.append(node)

    def initialize(self):
        self.frozen = True

        nodes = self.nodes
        tree = KDTree(len(nodes))

        for i, node in enumerate(nodes):
            tree.insert(node.point, i)

        tree.balance()
        processed = set()
        final_nodes = []
        groups = []

        for i in range(len(nodes)):
            if i in processed:
                continue

            # Find points to merge
            pending = [i]
            merge_set = set(pending)

            while pending:
                added = set()
                for j in pending:
                    for co, idx, dist in tree.find_range(nodes[j].point, self.epsilon):
                        added.add(idx)
                pending = added.difference(merge_set)
                merge_set.update(added)

            assert merge_set.isdisjoint(processed)

            processed.update(merge_set)

            # Group the points
            merge_list = [nodes[i] for i in merge_set]
            merge_list.sort(key=lambda x: x.name)

            group_class = merge_list[0].group_class

            for item in merge_list[1:]:
                cls = item.group_class

                if issubclass(cls, group_class):
                    group_class = cls
                elif not issubclass(group_class, cls):
                    raise MetarigError(
                        'Group class conflict: {} and {} from {} of {}'.format(
                            group_class, cls, item.name, item.rig.base_bone,
                        )
                    )

            group = group_class(merge_list)
            group.build(final_nodes)

            groups.append(group)

        self.final_nodes = self.rigify_sub_objects = final_nodes
        self.groups = groups


class MergeGroup(object):
    """Standard node group, merges nodes based on their restrictions and priorities."""

    def __init__(self, nodes):
        self.nodes = nodes

        for node in nodes:
            node.group = self

        def is_main(node):
            return isinstance(node, MainMergeNode)

        self.main_nodes = [n for n in nodes if is_main(n)]
        self.query_nodes = [n for n in nodes if not is_main(n)]

    def build(self, final_nodes):
        main_nodes = self.main_nodes

        # Sort nodes into rig buckets - can't merge within the same rig
        rig_table = collections.defaultdict(list)

        for node in main_nodes:
            rig_table[node.rig].append(node)

        # Build a 'can merge' table
        merge_table = { n: set() for n in main_nodes }

        for node in main_nodes:
            for rig, tgt_nodes in rig_table.items():
                if rig is not node.rig:
                    nodes = [n for n in tgt_nodes if node.can_merge_into(n)]
                    merge_table[max(nodes, key=node.get_merge_priority)].add(node)

        # Output groups starting with largest
        self.final_nodes = []

        pending = set(main_nodes)

        while pending:
            # Find largest group
            nodes = [n for n in main_nodes if n in pending]
            best = max(nodes, key=lambda n: len(merge_table[n]))
            child_set = merge_table[best]

            # Link children
            best.point = sum((c.point for c in child_set), best.point) / (len(child_set) + 1)

            for child in [n for n in main_nodes if n in child_set]:
                child.point = best.point
                best.merge_from(child)
                child.merge_into(best)

            final_nodes.append(best)
            self.final_nodes.append(best)

            best.merge_done()

            # Remove merged nodes from the table
            pending.remove(best)
            pending -= child_set

            for children in merge_table.values():
                children &= pending

        final_nodes += self.query_nodes


class BaseMergeNode(GenerateCallbackHost):
    """Base class of mergeable nodes."""

    merge_domain = None
    merger = NodeMerger
    group_class = MergeGroup

    def __init__(self, rig, name, point, *, domain=None):
        self.rig = rig
        self.name = name
        self.point = Vector(point)

        self.merger(rig.generator, domain or self.merge_domain).register_node(self)

    def can_merge_into(self, other):
        raise NotImplementedError()

    def get_merge_priority(self, other):
        return 0


class MainMergeNode(BaseMergeNode):
    """Base class of standard mergeable nodes."""

    def __init__(self, rig, name, point, *, domain=None):
        super().__init__(rig, name, point, domain=domain)

        self.merged_into = None
        self.merged = []

    def get_merged_siblings(self):
        master = self.merged_master
        return [master, *master.merged]

    def can_merge_into(self, other):
        return True

    def merge_into(self, other):
        self.merged_into = other

    def merge_from(self, other):
        self.merged.append(other)

    def merge_done(self):
        self.merged_master = self.merged_into or self

        for child in self.merged:
            child.merge_done()


class QueryMergeNode(BaseMergeNode):
    """Base class for special nodes used only to query which nodes are at a certain location."""

    def initialize(self):
        self.matched_nodes = [n for n in self.group.final_nodes if self.can_merge_into(n)]
        self.matched_nodes.sort(key=self.get_merge_priority, reverse=True)