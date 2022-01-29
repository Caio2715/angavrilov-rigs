# Experimental Rigify Feature Set

This provides a set of experimental Rigify rig types, some of which may be
included in Rigify in the future.

For the latest version that often requires the nightly master build of Blender,
use `Code > Download ZIP` to obtain a ZIP archive of the code, and install it
as a Feature Set through the Rigify Add-On settings.

Older versions are listed as [Tags](https://github.com/angavrilov/angavrilov-rigs/tags)
with matching .zip download links.

## Basic Rigs

Experimental rigs with a basic function.

### Center Of Mass (`basic.center_of_mass`)

Generates a bone that shows the approximate center of mass of the character,
computed based on bone positions. The set of bones and their own weights and
centers of mass are computed from a helper cage mesh.

* **Maximum Error** specifies the maximum deviation of the center from the ideal
  position that is acceptable if it allows reducing the number of bones. The error
  is caused by snapping centers of mass of bone components to the axis of the bone.
* **Volume Cage Mesh** specifies a mesh object to be used for computing masses of
  individual bones. The mesh must contain a separate manifold component for each
  bone, assigned to its vertex group. Each component must be assigned to exactly
  one bone: weight blending is not supported. It is possible to use any bone
  generated by the rig, without being limited to only DEF or ORG bones.
* **Add Sample Cage** creates a new valid cage mesh based on selected bones beside
  the active one. The vertex groups are mapped to ORG bones.

## Limb Rigs

### Extended Leg (`limbs.leg_plus`)

Adds experimental extensions to leg.

* **Toe Tip Roll** generates a slider to apply the forward roll to the toe.

**Runtime Options:**

* **Roll Forward On Toe** makes the toe roll forward on its tip.
* **IK->FK With Roll** snap button tries to snap IK to FK, using the heel roll
  control to preserve the current IK control orientation as much as possible.
  The operator allows selecting which roll channels to use via redo panel.
  Note: Currently, computing the 'roll on toe' slider value doesn't work well
  if both Roll and Yaw channels are used and nonzero.

### Extra Leg Heel (`limbs.extra_heel`)

Used as a child of a leg rig, this allows adding an alternative rest pose for
the foot and toe, with an appropriate foot roll mechanism. This can be useful
e.g. for providing a switch between low and high heel shoes in the same character.
The bone structure exactly matches that of leg, without anything above the foot.

The switch is controlled by a mandatory 'enabled' custom property that must be
placed on the base metarig bone of this component and rigged with a driver
(e.g. from a property placed on a custom 'root' bone). If multiple instances
of this rig are used for the same leg, it is up to the user to ensure that only
one of them can be 'enabled' at the same time.

The rig generates deform bones for convenience of skinning of objects based
on the alternative rest pose. These bones exactly overlap the positions of the
original leg deform bones during animation.

**Example file:** [demo-extra-heel.blend](https://www.dropbox.com/s/ll6ckj24yav6eyn/demo-extra-heel.blend?dl=0) demonstrates using this rig to implement a switch between low and high heel shoes via a property on the root bone.

### Spline IK Tentacle (`limbs.spline_tentacle`)

This rig type implements a tentacle with an IK system using the Spline IK constraint.
The controls define control points of a Bezier curve, and the bone chain follows the curve.

The curve control points are sorted into three groups: start, middle and end. The middle
controls are always visible and active, while the other two types can be shown and hidden
dynamically using properties; when enabled they appear next to the corresponding permanent
start/end control and can be moved from there.

* **Extra Start Controls** specifies the number of optional start controls to generate.
* **Middle Controls** specifies the number of middle controls to generate.
* **Extra End Controls** specifies the number of optional end controls to generate.
* Curve Fit Mode:
  + **Stretch To Fit** stretches the whole bone chain to fit the length of the curve defined
    by the controls.
  + **Direct Tip Control** turns the last bone of the chain into the end control, allowing
    direct control over that bone, while the middle bones stretch to follow the curve and
    cover the gap. This is similar to how regular IK works for limbs.
  + **Manual Squash & Stretch** allows full manual control over the chain scaling, while the
    chain covers as much of the curve as it can given its current length.
* **Radius Scaling** allows scaling the controls to control the thickness of the chain through the curve.
* **Maximum Radius** specifies the maximum scale allowed by the *Radius Scaling* feature.
* **FK Controls** generates an FK control chain and IK-FK snapping.

**Runtime Options:**

* **Start Controls** changes the number of visible optional start controls.
* **End Controls** changes the number of visible optional end controls.
* **End Twist Fix** (Direct Tip Control only)
  For technical reasons, the rig can only determine the chain twist from the tip control
  within the -180..180 degrees range. Exceeding that flips the twist direction.
  This option allows working around the limitation by dialing in a rough estimate of
  twist in full rotations, and letting the rig auto-correct to the precise value within
  the 180 degrees range from the estimate.

## Spine Rigs

### BlenRig-like Spine (`spines.blenrig_spine`)

This implements an IK spine rig with controls behaving similar to BlenRig.

* **Custom Pivot Control** generates a movable pivot control for the torso.
* **Custom Hips Pivot** generates a movable pivot for the hip control.

**Runtime Options:**

* **FK Hips** allows the main hip control to fully control rotation of the hip bone.
* **FK Chest** releases the FK controls of the top of the spine from the IK mechanism.

## Body IK Rigs

In some rare cases, like crawling, it may be desirable to have IK controls that lock
the location of elbows/knees by adjusting the spine and shoulders. This group of
rigs contains extended versions of spine, shoulder, arm and leg rigs that provide
this functionality. Legs must be used in pair with a spine, and arms with shoulders.

**Example file:** https://blendswap.com/blend/29534 demonstrates Body IK and a number of other features via two fully usable sample characters.

### Spines

The feature set provides `body_ik.basic_spine` and `body_ik.blenrig_spine`, which
are extended versions of the standard spine and the BlenRig-like spine from this
feature set. They behave the same as the originals, except that they work with
the Body IK leg rig.

**Runtime Options:**

* **Snap To Hip IK** applies the adjustment from the Knee IK to the controls.

**Runtime Options (`body_ik.blenrig_spine`):**

Due to the way BlenRig spine works, it is possible to apply the effect of IK by
either offsetting the whole spine, or just the hip control.

* **Body IK Hips** switches to offsetting just the hip control.
* **Snap Hips To Hip IK** applies the hip control adjustment.

### Shoulder

The `body_ik.shoulder` rig implements a simple IK-compatible shoulder.

### Limbs

The `body_ik.arm` and `body_ik.leg` rigs extend the standard limbs to implement
the elbow/knee IK functionality. The rigs provide a second set of IK controls
mapped to the elbow/knee, and options for switching and IK-FK snapping.

The special IK is intended for poses that are very different from the default
rest pose, so it doesn't work that well if switched on immediately from rest.
For best result, the character should be pre-posed into a kneeling/crawling
pose using FK, and then switched to the IK controls using snapping. Knee IK
is also not stable for mathematical reasons when both legs are enabled and
the shins are parallel (basically there are infinitely many solutions and
it becomes confused).

Note: the leg is based on `limbs.leg_plus` above.

**Runtime Options:**

* **IK Force Straight** enables the mechanism in the spine/shoulder to keep
  the limb fully extended with ordinary IK. This is obviously mutually exclusive
  with using the actual knee/elbow IK.

## Jiggle Rigs

These are rigs to provide jiggle behavior.

### Basic Jiggle (`jiggle.basic`)

Creates two grab controls with the deform bone automatically stretching between them.

The chain should consist of one or two bones. If present, constraints on
the ORG bones are transplanted to helper parent bones for the controls.

* **Master Control** generates a parent master control for the jiggle setup.
* **Follow Front** adds a constraint to apply part of the motion of the front control to the back.

### Cloth Jiggle (`jiggle.cloth_cage`)

A version of basic jiggle with support for a cloth simulation cage
that is used to deform a part of the final mesh via Surface Deform.

The intended setup is that the jiggle rig is used to deform the cage,
which permanently controls part of the final mesh, and has a simulation
that can be enabled and adjusted using the custom properties. To allow
attaching additional directly animated objects to the affected area, the
rig supports a feedback mechanism from the cage to the front control.

Custom properties on the cage object and mesh that have names starting
with 'option_' are automatically copied to the rig bone and linked
with drivers. Anchor empties parented to the cage are used to feed
the result of cloth simulation and/or cage shape keys to the rig.

Resetting all custom properties on the cage object and mesh to defaults,
and disabling the Armature modifier must always reconfigure it and the
anchors into the rest shape that the rig should bind to.

The cage can only depend on the first deform bone of this rig, while
the second deform is driven by cage feedback and should be used to
help transition between the cage affected area and pure bone rigging
on the main mesh.

* **Cloth Cage Mesh** (_required_) specifies the cage mesh object.
* **Front Anchor** specifies the empty parented to the cage and used for feeding
  motion of its front area back to the rig.
* **Shape Anchor** specifies an optional empty used to adjust the rig to the
  effect of shape keys pre-configuring the shape of the cage, using a linked
  duplicate based setup.
* **Only Use Shape Anchor Location** tells the rig to only use the translation
  of the shape anchor object for a simpler mechanism.

**Example file:** [demo-breast-jiggle.blend](https://www.dropbox.com/s/k0n0vjigd19c3ns/demo-breast-jiggle.blend?dl=1)
with included detailed text instructions demonstrates applying this in a breast rig
for a character with a clothing switch option (uses only a torso to reduce file size).

## Skin Rigs (Experimental)

These rigs implement a flexible system for rigging skin using multiple interacting
B-Bone chains. This is developed as a replacement for the Rigify face rig.

The core part of the skin system has been moved to Rigify and is documented
in the [Blender Manual](https://docs.blender.org/manual/en/dev/addons/rigging/rigify/rig_types/skin.html)
for users, and on the [Blender Wiki](https://wiki.blender.org/wiki/Process/Addons/Rigify/RigUtils/Skin)
for scripters.

### Elastic Stretch Transform (`skin.transform.elastic_stretch`)

This rig applies the math behind the Elastic Deform sculpt brush to
its child chain control positions when its own control is scaled.

This should produce somewhat realistic stretching, but at high scale
factors scaling becomes uneven and eventually forms folds as some
inner controls overtake outer ones.

**Example file:** [demo-elastic-stretch.blend](https://www.dropbox.com/s/a1xjwqfd7zkxoc1/demo-elastic-stretch.blend?dl=0) demonstrates multiple concentric loops controlled via this rig.

* **Generate Control** specifies whether to generate a visible control,
  or use the transformation of the ORG bone as a part of more complex
  ad-hoc rig setup.
* **Exact Scale Radius** specifies the radius of the brush via the
  distance from center at which control bone scale is applied exactly.

### Concentric Stretch Transform (`skin.transform.concentric_stretch`)

As opposed to the elastic transformation, this rig operates specifically
on concentric loops, scaling them in such a way that stretching and
compression is evenly fading out from center, and inner loops don't
overtake outer ones.

The loops must be formed by L/R symmetry chains, and are expected to
be (nearly) elliptical and centered on the control bone. It is acceptable
to use spliced ellipses with different extents in the local Z direction,
but the X direction must be symmetrical.

**Example file:** [demo-concentric-stretch.blend](https://www.dropbox.com/s/hdof6t7vm3nx1ds/demo-concentric-stretch.blend?dl=0) demonstrates multiple concentric loops controlled via this rig.

* **Generate Control** specifies whether to generate a visible control,
  or use the transformation of the ORG bone as a part of more complex
  ad-hoc rig setup.
* **Squash Limit** specifies how small each gap between loops can be
  squashed in the X and Z direction correspondingly.
* **Layer Fade** specifies the per loop falloff of the influence of
  translating the control.
* **Circularize Inner Shape** specifies that instead of simply controlling
  the innermost loop directly, the rig should delay the onset of upscale
  on its larger dimension until it becomes a circle.
* **Rhombus Correction** applies correction to widen loops that have
  rhombic rather than elliptical shape into ellipses, as their inner
  loops are scaled up and fill more space.
