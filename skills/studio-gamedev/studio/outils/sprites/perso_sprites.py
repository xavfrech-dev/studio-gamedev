# -*- coding: utf-8 -*-
"""
Personnage « chibi » du studio : modèle, armature, accessoires, animations et rendu des images brutes.

Lancement (Blender 4.5, un seul à la fois) :
  blender --background --factory-startup --python perso_sprites.py -- --sortie ./sprites_brut [--test] [--anims marche,repos] [--acc casquette,...]

Ce script produit, pour chaque animation / image / direction, des PNG 256×256 bruts :
  <anim>/corps/fFFdD_base_0001.png   rendu ombré (zones recolorables en blanc)
  <anim>/corps/fFFdD_mA_0001.png     masques R=peau G=cheveux B=haut (couverture linéaire)
  <anim>/corps/fFFdD_mB_0001.png     masques R=bas G=chaussures B=(inutilisé)
  <anim>/<acc>/fFFdD_base_0001.png   accessoire seul, le corps en « holdout » (occlusion exacte)
  <anim>/<acc>/fFFdD_mB_0001.png     masque de l'accessoire (canal B)
et ancres.json (ancres pieds, tête, mains, siège, clavier en pixels 256).
L'assemblage des planches est fait par assembler.py (Python + Pillow, hors Blender).

Repère : 1 unité Blender = 1 case du studio. Blender (X, Y, Z) = studio (x, -y, z).
Caméra orthographique : élévation 30°, azimut 45° → losange 2:1 exact du studio (TW=32, TH=16).
Échelle : 256 px ↔ 3,5 × le pixel studio (zoom 1) ; 128 px ↔ 1,75 ×.
"""
import bpy, bmesh, sys, os, json, math, time
from mathutils import Vector, Matrix, Euler, Quaternion
from bpy_extras.object_utils import world_to_camera_view
for _flux in (sys.stdout, sys.stderr):                 # S6 : sortie en UTF-8, même redirigée (Windows)
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# ------------------------------------------------------------------------------------------
# Arguments
# ------------------------------------------------------------------------------------------
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(nom, defaut=None):
    if nom in argv:
        i = argv.index(nom)
        return argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith('--') else True
    return defaut
SORTIE = arg('--sortie', os.path.abspath('sprites_brut'))
TEST = bool(arg('--test', False))
BLEND = arg('--blend', None)          # enregistre le .blend du modèle (facultatif)

RES = 256                             # rendu brut ; 128 obtenu par réduction 2×2
TW, TH = 32.0, 16.0
PX_STUDIO = TW * math.sqrt(2)         # 45,25 px studio par unité (perpendiculaire à la vue)
FACTEUR = 3.5                         # px du rendu 256 par px studio (zoom 1)
ORTHO = RES / (PX_STUDIO * FACTEUR)
ANCRE_PIEDS = (128, 224)              # pixel (256) du point au sol sous le personnage

# ------------------------------------------------------------------------------------------
# Couleurs
# ------------------------------------------------------------------------------------------
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)
ENCRE = '#2B2620'

# ------------------------------------------------------------------------------------------
# Scène
# ------------------------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
vl = bpy.context.view_layer
for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        sc.render.engine = eng; break
    except TypeError:
        pass
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.filter_size = 1.2
sc.eevee.taa_render_samples = 16
try: sc.eevee.use_shadows = False
except Exception: pass
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.frame_current = 1

monde = bpy.data.worlds.new('Monde'); sc.world = monde
monde.use_nodes = True
monde.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

# Lumière : vient du côté +y studio (gauche de l'écran) et d'en haut, comme les faces des meubles
# du studio (dessus clair, face +y moyenne, face +x sombre).
sol = bpy.data.lights.new('Soleil', 'SUN'); sol.energy = math.pi; sol.use_shadow = False
try: sol.angle = 0.2
except Exception: pass
o_sol = bpy.data.objects.new('Soleil', sol); sc.collection.objects.link(o_sol)
L_DIR = Vector((-0.35, -0.85, 1.25)).normalized()
o_sol.rotation_euler = L_DIR.to_track_quat('Z', 'Y').to_euler()

cam_d = bpy.data.cameras.new('Iso'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ORTHO
cam_d.shift_x = (ANCRE_PIEDS[0] - RES / 2) / RES * -1.0
cam_d.shift_y = (ANCRE_PIEDS[1] - RES / 2) / RES
cam_d.clip_start = 0.1; cam_d.clip_end = 100
cam = bpy.data.objects.new('Iso', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (math.radians(60), 0, math.radians(45))
avant = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
cam.location = -avant * 12

# AOV des masques
for n in ('mA', 'mB'):
    a = vl.aovs.add(); a.name = n; a.type = 'COLOR'

# ------------------------------------------------------------------------------------------
# Matériaux « cartoon » : diffus → Shader to RGB → rampe 2 tons douce → × couleur → émission
# ------------------------------------------------------------------------------------------
OMBRE = lin('#B7A9A6')[:3]       # ton d'ombre légèrement chaud/rosé (multiplié par la couleur)
MI = lin('#E4DAD2')[:3]
def materiau(nom, couleur, mA=(0, 0, 0), mB=(0, 0, 0)):
    m = bpy.data.materials.new(nom); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    dif = N.new('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = N.new('ShaderNodeShaderToRGB'); Lk.new(dif.outputs[0], s2r.inputs[0])
    rp = N.new('ShaderNodeValToRGB'); r = rp.color_ramp; r.interpolation = 'EASE'
    r.elements[0].position = 0.10; r.elements[0].color = OMBRE + (1,)
    e = r.elements.new(0.22); e.color = MI + (1,)
    r.elements[1].position = 0.42; r.elements[1].color = (1, 1, 1, 1)
    Lk.new(s2r.outputs['Color'], rp.inputs['Fac'])
    mul = N.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY'
    Lk.new(rp.outputs['Color'], mul.inputs[0]); mul.inputs[1].default_value = couleur[:3]
    em = N.new('ShaderNodeEmission'); Lk.new(mul.outputs[0], em.inputs['Color']); em.inputs['Strength'].default_value = 1
    Lk.new(em.outputs[0], out.inputs['Surface'])
    for nomA, val in (('mA', mA), ('mB', mB)):
        if any(val):
            ao = N.new('ShaderNodeOutputAOV'); ao.aov_name = nomA
            ao.inputs['Color'].default_value = tuple(val) + (1,)
    return m

BLANC = (1, 1, 1, 1)
MAT = {
    'peau': materiau('peau', BLANC, mA=(1, 0, 0)),
    'cheveux': materiau('cheveux', BLANC, mA=(0, 1, 0)),
    'haut': materiau('haut', BLANC, mA=(0, 0, 1)),
    'bas': materiau('bas', BLANC, mB=(1, 0, 0)),
    'chaussures': materiau('chaussures', BLANC, mB=(0, 1, 0)),
    'acc': materiau('acc', BLANC, mB=(0, 0, 1)),
    'yeux': materiau('yeux', lin('#231a14')),
    'joues': materiau('joues', lin('#e89a86')),
    'bouche': materiau('bouche', lin('#7a3a2c')),
    'tasse': materiau('tasse', lin('#f2ece0')),
    'tasse_bande': materiau('tasse_bande', lin('#2f4a3a')),
    'cafe': materiau('cafe', lin('#4a2e1c')),
    'laiton': materiau('laiton', lin('#c9953e')),
    'bois': materiau('bois', lin('#7a4e2e')),
    'manette': materiau('manette', lin('#3a3a42')),
    'bouton_r': materiau('bouton_r', lin('#c0503a')),
    'bouton_v': materiau('bouton_v', lin('#6fa75c')),
    'coussin': materiau('coussin', lin('#2a2a2e')),
}
contour = bpy.data.materials.new('contour'); contour.use_nodes = True
nt = contour.node_tree; nt.nodes.clear()
o_ = nt.nodes.new('ShaderNodeOutputMaterial'); em_ = nt.nodes.new('ShaderNodeEmission')
em_.inputs['Color'].default_value = lin(ENCRE); nt.links.new(em_.outputs[0], o_.inputs['Surface'])
contour.use_backface_culling = True
try: contour.use_backface_culling_shadow = True
except Exception: pass
EPAIS = 0.0115                   # ≈ 1,8 px à 256, 0,9 px à 128

# ------------------------------------------------------------------------------------------
# Collections
# ------------------------------------------------------------------------------------------
def collection(nom):
    c = bpy.data.collections.new(nom); sc.collection.children.link(c); return c
C_CORPS = collection('Corps')
C_OBJETS = collection('Objets')
ACCS = ['casquette', 'bonnet', 'chapeau_conique', 'casque_audio', 'lunettes', 'beret', 'barbe']
C_ACC = {a: collection('Acc_' + a) for a in ACCS}

# ------------------------------------------------------------------------------------------
# Géométrie
# ------------------------------------------------------------------------------------------
def finir(ob, mat, coll, trait=True, lisse=True):
    me = ob.data
    me.materials.append(mat)
    if lisse:
        for p in me.polygons: p.use_smooth = True
    if trait:
        me.materials.append(contour)
        mod = ob.modifiers.new('Contour', 'SOLIDIFY')
        mod.thickness = EPAIS; mod.offset = 1.0; mod.use_flip_normals = True
        mod.material_offset = 1; mod.use_rim = False
    coll.objects.link(ob)
    return ob

def sphere_bm(seg=28, ring=14):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1.0)
    return bm

def ellipsoide(nom, centre, rayons, mat, coll, rot=(0, 0, 0), trait=True, seg=28, ring=14, coupe=None):
    bm = sphere_bm(seg, ring)
    if coupe is not None:      # garde z >= coupe (sphère unité) : dômes
        geom = [v for v in bm.verts if v.co.z < coupe - 1e-6]
        for v in geom: v.co.z = coupe
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for v in bm.verts: v.co = Vector((v.co.x * rayons[0], v.co.y * rayons[1], v.co.z * rayons[2]))
    me = bpy.data.meshes.new(nom); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nom, me)
    ob.matrix_world = Matrix.Translation(Vector(centre)) @ Euler(rot).to_matrix().to_4x4()
    return finir(ob, mat, coll, trait)

def capsule(nom, p0, p1, r0, r1, mat, coll, trait=True):
    p0, p1 = Vector(p0), Vector(p1); L = (p1 - p0).length
    bm = sphere_bm(20, 12)
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((x * r1, y * r1, z * r1 + L)) if z > 0 else Vector((x * r0, y * r0, z * r0))
    me = bpy.data.meshes.new(nom); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nom, me)
    q = Vector((0, 0, 1)).rotation_difference((p1 - p0).normalized())
    ob.matrix_world = Matrix.Translation(p0) @ q.to_matrix().to_4x4()
    return finir(ob, mat, coll, trait)

def tore(nom, centre, R, r, mat, coll, rot=(0, 0, 0), trait=True, arc=None, maj=32, mino=10):
    bm = bmesh.new()
    verts = []
    a0, a1 = (0, 2 * math.pi) if arc is None else arc
    ferme = arc is None
    n = maj if ferme else maj + 1
    for i in range(n):
        u = a0 + (a1 - a0) * i / (maj if ferme else maj)
        anneau = []
        for j in range(mino):
            w = 2 * math.pi * j / mino
            x = (R + r * math.cos(w)) * math.cos(u); y = (R + r * math.cos(w)) * math.sin(u); z = r * math.sin(w)
            anneau.append(bm.verts.new((x, y, z)))
        verts.append(anneau)
    for i in range(n if ferme else n - 1):
        A = verts[i]; B = verts[(i + 1) % n]
        for j in range(mino):
            bm.faces.new((A[j], B[j], B[(j + 1) % mino], A[(j + 1) % mino]))
    if not ferme:
        for anneau in (verts[0], verts[-1]):
            c = bm.verts.new(sum((v.co for v in anneau), Vector()) / mino)
            for j in range(mino): bm.faces.new((anneau[j], anneau[(j + 1) % mino], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(nom); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nom, me)
    ob.matrix_world = Matrix.Translation(Vector(centre)) @ Euler(rot).to_matrix().to_4x4()
    return finir(ob, mat, coll, trait)

def cylindre(nom, centre, r, h, mat, coll, rot=(0, 0, 0), trait=True, r2=None, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    me = bpy.data.meshes.new(nom); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(nom, me)
    ob.matrix_world = Matrix.Translation(Vector(centre)) @ Euler(rot).to_matrix().to_4x4()
    return finir(ob, mat, coll, trait, lisse=False)

# ------------------------------------------------------------------------------------------
# Squelette au repos (repère du personnage : avant = -Y, gauche = +X, haut = +Z)
# ------------------------------------------------------------------------------------------
HANCHE_Z = 0.38; EPAULE_Z = 0.705; COU_Z = 0.775; TETE_C = 0.94; R_TETE = 0.165
K_TETE = R_TETE / 0.158          # les pièces de tête sont dessinées pour R=0,158 puis mises à l'échelle
L_BRAS, L_AVBRAS = 0.13, 0.12
L_CUISSE, L_TIBIA = 0.16, 0.15
CHEVILLE_Z = 0.07
EP_X, HA_X = 0.13, 0.064
H0 = HANCHE_Z
OS = {   # nom : (tête, queue)
    'racine': ((0, 0, 0), (0, -0.15, 0)),
    'bassin': ((0, 0, HANCHE_Z), (0, 0, HANCHE_Z + 0.05)),
    'torse': ((0, 0, HANCHE_Z + 0.05), (0, 0, COU_Z)),
    'tete': ((0, 0, COU_Z), (0, 0, TETE_C + 0.17)),
}
for s, c in ((1, 'L'), (-1, 'R')):
    ex, hx = s * EP_X, s * HA_X
    OS['bras.' + c] = ((ex, 0, EPAULE_Z), (ex, 0, EPAULE_Z - L_BRAS))
    OS['avbras.' + c] = ((ex, 0, EPAULE_Z - L_BRAS), (ex, 0, EPAULE_Z - L_BRAS - L_AVBRAS))
    OS['main.' + c] = ((ex, 0, EPAULE_Z - L_BRAS - L_AVBRAS), (ex, 0, EPAULE_Z - L_BRAS - L_AVBRAS - 0.06))
    OS['cuisse.' + c] = ((hx, 0, HANCHE_Z), (hx, 0, HANCHE_Z - L_CUISSE))
    OS['tibia.' + c] = ((hx, 0, HANCHE_Z - L_CUISSE), (hx, 0, CHEVILLE_Z))
    OS['pied.' + c] = ((hx, 0, CHEVILLE_Z), (hx, -0.1, CHEVILLE_Z))

arm_d = bpy.data.armatures.new('Squelette')
arm = bpy.data.objects.new('Squelette', arm_d); sc.collection.objects.link(arm)
vl.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for nom, (t, q) in OS.items():
    eb = arm_d.edit_bones.new(nom); eb.head = t; eb.tail = q; eb.roll = 0
for nom in OS:
    if nom != 'racine': arm_d.edit_bones[nom].parent = arm_d.edit_bones['racine']
bpy.ops.object.mode_set(mode='OBJECT')
REPOS = {b.name: b.matrix_local.copy() for b in arm_d.bones}

def accrocher(ob, os_nom):
    mw = ob.matrix_world.copy()
    ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = os_nom
    b = arm_d.bones[os_nom]
    if os_nom == 'tete':
        c = Matrix.Translation((0, 0, TETE_C))
        mw = c @ Matrix.Scale(K_TETE, 4) @ c.inverted() @ mw
    ob.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
    ob.matrix_basis = mw

# ------------------------------------------------------------------------------------------
# Modèle
# ------------------------------------------------------------------------------------------
def construire_corps():
    C = C_CORPS
    # bassin et torse (forme de haricot douce)
    accrocher(ellipsoide('Bassin', (0, 0.006, HANCHE_Z + 0.03), (0.118, 0.094, 0.082), MAT['bas'], C), 'bassin')
    t = ellipsoide('Torse', (0, 0, 0.575), (0.124, 0.098, 0.17), MAT['haut'], C)
    me = t.data      # rétrécit doucement le haut du torse (épaules arrondies), élargit le bas
    for v in me.vertices:
        k = 1.0 - 0.08 * max(0.0, v.co.z / 0.17) + 0.05 * max(0.0, -v.co.z / 0.17)
        v.co.x *= k; v.co.y *= k
    accrocher(t, 'torse')
    accrocher(capsule('Cou', (0, 0.004, 0.70), (0, 0.004, 0.80), 0.045, 0.045, MAT['peau'], C), 'torse')
    # tête
    accrocher(ellipsoide('Tete', (0, 0, TETE_C), (R_TETE, R_TETE * 0.96, R_TETE * 0.97), MAT['peau'], C, seg=32, ring=16), 'tete')
    accrocher(ellipsoide('Cheveux', (0, 0.018, TETE_C + 0.024), (0.168, 0.162, 0.162), MAT['cheveux'], C, seg=32, ring=16), 'tete')
    accrocher(ellipsoide('Frange', (0, -0.112, TETE_C + 0.098), (0.128, 0.05, 0.06), MAT['cheveux'], C, rot=(math.radians(-38), 0, 0)), 'tete')
    for s, c in ((1, 'L'), (-1, 'R')):
        accrocher(ellipsoide('Meche.' + c, (s * 0.115, -0.085, TETE_C + 0.025), (0.045, 0.05, 0.055), MAT['cheveux'], C, rot=(math.radians(-25), s * math.radians(20), 0)), 'tete')
        accrocher(ellipsoide('Oreille.' + c, (s * 0.156, 0.004, TETE_C - 0.012), (0.024, 0.034, 0.036), MAT['peau'], C), 'tete')
        # yeux posés sur la sphère de la tête
        d = Vector((s * 0.37, -1.0, -0.16)).normalized()
        pos = Vector((0, 0, TETE_C)) + Vector((d.x * R_TETE, d.y * R_TETE * 0.96, d.z * R_TETE * 0.97)) * 0.985
        q = Vector((0, -1, 0)).rotation_difference(d)
        oe = ellipsoide('Oeil.' + c, pos, (0.019, 0.012, 0.03), MAT['yeux'], C, trait=False, seg=12, ring=8)
        oe.matrix_world = Matrix.Translation(pos) @ q.to_matrix().to_4x4()
        accrocher(oe, 'tete')
        d2 = Vector((s * 0.58, -1.0, -0.42)).normalized()
        pos2 = Vector((0, 0, TETE_C)) + Vector((d2.x * R_TETE, d2.y * R_TETE * 0.96, d2.z * R_TETE * 0.97)) * 0.99
        oj = ellipsoide('Joue.' + c, pos2, (0.024, 0.008, 0.014), MAT['joues'], C, trait=False, seg=12, ring=8)
        oj.matrix_world = Matrix.Translation(pos2) @ Vector((0, -1, 0)).rotation_difference(d2).to_matrix().to_4x4()
        accrocher(oj, 'tete')
    d3 = Vector((0, -1.0, -0.5)).normalized()
    pos3 = Vector((0, 0, TETE_C)) + Vector((0, d3.y * R_TETE * 0.96, d3.z * R_TETE * 0.97)) * 0.99
    ob = ellipsoide('Bouche', pos3, (0.016, 0.006, 0.007), MAT['bouche'], C, trait=False, seg=12, ring=8)
    ob.matrix_world = Matrix.Translation(pos3) @ Vector((0, -1, 0)).rotation_difference(d3).to_matrix().to_4x4()
    accrocher(ob, 'tete')
    # membres
    for s, c in ((1, 'L'), (-1, 'R')):
        ex, hx = s * EP_X, s * HA_X
        e0 = Vector((ex, 0, EPAULE_Z)); e1 = e0 - Vector((0, 0, L_BRAS)); e2 = e1 - Vector((0, 0, L_AVBRAS))
        accrocher(ellipsoide('Epaule.' + c, e0, (0.052, 0.052, 0.052), MAT['haut'], C), 'bras.' + c)
        accrocher(capsule('Bras.' + c, e0, e1, 0.048, 0.044, MAT['haut'], C), 'bras.' + c)
        accrocher(capsule('AvBras.' + c, e1, e2, 0.044, 0.04, MAT['haut'], C), 'avbras.' + c)
        accrocher(ellipsoide('Main.' + c, e2 - Vector((0, 0, 0.03)), (0.047, 0.044, 0.05), MAT['peau'], C), 'main.' + c)
        h0 = Vector((hx, 0, HANCHE_Z)); h1 = h0 - Vector((0, 0, L_CUISSE)); h2 = Vector((hx, 0, CHEVILLE_Z))
        accrocher(capsule('Cuisse.' + c, h0, h1, 0.064, 0.058, MAT['bas'], C), 'cuisse.' + c)
        accrocher(capsule('Tibia.' + c, h1, h2, 0.057, 0.05, MAT['bas'], C), 'tibia.' + c)
        accrocher(ellipsoide('Chaussure.' + c, (hx, -0.03, CHEVILLE_Z - 0.026), (0.058, 0.092, 0.05), MAT['chaussures'], C, coupe=-0.55), 'pied.' + c)

def construire_accessoires():
    T = TETE_C
    A = C_ACC['casquette']
    accrocher(ellipsoide('Casq_dome', (0, 0.004, T + 0.03), (0.2, 0.198, 0.185), MAT['acc'], A, coupe=0.05), 'tete')
    accrocher(ellipsoide('Casq_visiere', (0, -0.175, T + 0.045), (0.125, 0.105, 0.014), MAT['acc'], A, rot=(math.radians(10), 0, 0)), 'tete')
    accrocher(ellipsoide('Casq_bouton', (0, 0.008, T + 0.197), (0.02, 0.02, 0.012), MAT['acc'], A), 'tete')
    A = C_ACC['bonnet']
    accrocher(ellipsoide('Bonnet', (0, 0.006, T + 0.03), (0.2, 0.198, 0.2), MAT['acc'], A, rot=(math.radians(4), 0, 0), coupe=0.08), 'tete')
    accrocher(tore('Bonnet_bord', (0, 0.006, T + 0.045), 0.188, 0.028, MAT['acc'], A, rot=(math.radians(4), 0, 0)), 'tete')
    accrocher(ellipsoide('Bonnet_pompon', (0, -0.01, T + 0.235), (0.045, 0.045, 0.045), MAT['acc'], A), 'tete')
    A = C_ACC['chapeau_conique']
    accrocher(cylindre('Chapeau', (0, 0.0, T + 0.21), 0.31, 0.18, MAT['acc'], A, r2=0.012, seg=36), 'tete')
    accrocher(ellipsoide('Chapeau_pointe', (0, 0.0, T + 0.30), (0.018, 0.018, 0.012), MAT['acc'], A, trait=False), 'tete')
    A = C_ACC['casque_audio']
    accrocher(tore('Arceau', (0, 0.0, T), 0.176, 0.016, MAT['acc'], A, rot=(math.radians(90), 0, 0), arc=(math.radians(-5), math.radians(185))), 'tete')
    for s in (1, -1):
        accrocher(cylindre('Ecouteur%d' % s, (s * 0.168, 0.0, T - 0.01), 0.058, 0.04, MAT['acc'], A, rot=(0, math.radians(90), 0)), 'tete')
        accrocher(cylindre('Coussin%d' % s, (s * 0.148, 0.0, T - 0.01), 0.048, 0.018, MAT['coussin'], A, rot=(0, math.radians(90), 0), trait=False), 'tete')
    A = C_ACC['lunettes']
    for s in (1, -1):
        accrocher(tore('Verre%d' % s, (s * 0.057, -0.168, T - 0.012), 0.034, 0.0095, MAT['acc'], A, rot=(math.radians(90), 0, s * math.radians(-12)), trait=False, mino=8), 'tete')
        accrocher(capsule('Branche%d' % s, (s * 0.09, -0.16, T - 0.004), (s * 0.155, -0.02, T + 0.0), 0.007, 0.007, MAT['acc'], A, trait=False), 'tete')
    accrocher(tore('Pont', (0, -0.17, T - 0.01), 0.026, 0.007, MAT['acc'], A, rot=(math.radians(90), 0, 0), arc=(math.radians(35), math.radians(145)), trait=False, mino=6), 'tete')
    A = C_ACC['beret']
    accrocher(ellipsoide('Beret', (0.02, 0.012, T + 0.135), (0.185, 0.18, 0.06), MAT['acc'], A, rot=(math.radians(-6), math.radians(-14), 0)), 'tete')
    accrocher(ellipsoide('Beret_queue', (0.01, 0.012, T + 0.198), (0.012, 0.012, 0.022), MAT['acc'], A), 'tete')
    A = C_ACC['barbe']
    b = ellipsoide('Barbe', (0, -0.035, T - 0.075), (0.15, 0.135, 0.105), MAT['acc'], A, seg=32, ring=16)
    me = b.data      # ne garde que l'avant-bas (mâchoire)
    bm = bmesh.new(); bm.from_mesh(me)
    sup = [v for v in bm.verts if v.co.y > -0.02 or v.co.z > 0.045]
    bmesh.ops.delete(bm, geom=sup, context='VERTS'); bm.to_mesh(me); bm.free()
    b.modifiers['Contour'].use_rim = False
    sol_ = b.modifiers.new('Epais', 'SOLIDIFY'); sol_.thickness = 0.02; sol_.offset = -1
    b.modifiers.move(1, 0)
    accrocher(b, 'tete')

OBJETS = {}
def construire_objets():
    C = C_OBJETS
    def groupe(nom, parts):
        e = bpy.data.objects.new(nom, None); C.objects.link(e)
        e.parent = arm
        for p in parts:
            mw = p.matrix_world.copy(); p.parent = e; p.matrix_parent_inverse = Matrix.Identity(4); p.matrix_basis = mw
        OBJETS[nom] = e
        return e
    # tasse (origine = centre de la tasse)
    groupe('tasse', [
        cylindre('Tasse', (0, 0, 0), 0.032, 0.07, MAT['tasse'], C),
        cylindre('Tasse_bande', (0, 0, 0.005), 0.0335, 0.016, MAT['tasse_bande'], C, trait=False),
        cylindre('Tasse_cafe', (0, 0, 0.0352), 0.027, 0.001, MAT['cafe'], C, trait=False),
        tore('Tasse_anse', (0.036, 0, 0.0), 0.018, 0.006, MAT['tasse'], C, rot=(math.radians(90), 0, 0)),
    ])
    # cloche (origine = poignée tenue)
    groupe('cloche', [
        capsule('Cloche_manche', (0, 0, -0.01), (0, 0, 0.06), 0.012, 0.014, MAT['bois'], C),
        cylindre('Cloche', (0, 0, -0.05), 0.02, 0.06, MAT['laiton'], C, r2=0.045),
        ellipsoide('Cloche_battant', (0, 0, -0.085), (0.012, 0.012, 0.012), MAT['laiton'], C, trait=False),
    ])
    # manette (origine = centre)
    groupe('manette', [
        ellipsoide('Manette', (0, 0, 0), (0.07, 0.03, 0.018), MAT['manette'], C),
        ellipsoide('Manette_g', (0.055, 0.012, -0.004), (0.026, 0.03, 0.02), MAT['manette'], C),
        ellipsoide('Manette_d', (-0.055, 0.012, -0.004), (0.026, 0.03, 0.02), MAT['manette'], C),
        ellipsoide('Bouton_r', (-0.03, -0.006, 0.016), (0.009, 0.009, 0.005), MAT['bouton_r'], C, trait=False),
        ellipsoide('Bouton_v', (-0.045, 0.004, 0.016), (0.009, 0.009, 0.005), MAT['bouton_v'], C, trait=False),
    ])

construire_corps()
construire_accessoires()
construire_objets()

# ------------------------------------------------------------------------------------------
# Cinématique : pose analytique (FK du tronc, IK à 2 os pour bras et jambes)
# ------------------------------------------------------------------------------------------
def V(x, f, z): return Vector((x, -f, z))           # x = gauche du perso, f = avant, z = haut
def Rx(a): return Matrix.Rotation(a, 3, 'X')
def Ry(a): return Matrix.Rotation(a, 3, 'Y')
def Rz(a): return Matrix.Rotation(a, 3, 'Z')

def ik2(S, T, a, b, pole):
    d = T - S; L = d.length
    L = max(1e-4, min(L, a + b - 1e-4)); dirv = d.normalized()
    ca = (a * a + L * L - b * b) / (2 * a * L); ca = max(-1, min(1, ca)); sa = math.sqrt(1 - ca * ca)
    n = (pole - S); n = n - dirv * n.dot(dirv)
    n = n.normalized() if n.length > 1e-6 else Vector((0, -1, 0))
    E = S + dirv * (a * ca) + n * (a * sa)
    return E, S + dirv * L

class Pose:
    def __init__(s):
        s.bassin = V(0, 0, H0 - 0.006); s.b_yaw = 0; s.b_pitch = 0; s.b_roll = 0
        s.lean = 0.0; s.t_roll = 0; s.t_yaw = 0
        s.h_pitch = 0; s.h_yaw = 0; s.h_roll = 0
        s.mains = {}; s.coudes = {}; s.pieds = {}; s.genoux = {}; s.pied_pitch = {1: 0, -1: 0}
        s.objets = {}            # nom -> Matrix (repère perso)
        s.epaule_dz = 0.0

def appliquer(p):
    pb = arm.pose.bones
    def poser(nom, tete, R):
        pb[nom].matrix = Matrix.Translation(tete) @ (R @ REPOS[nom].to_3x3()).to_4x4()
    Rb = Rz(p.b_yaw) @ Rx(p.b_pitch) @ Ry(p.b_roll)
    poser('bassin', p.bassin, Rb)
    base_t = p.bassin + Rb @ Vector((0, 0, 0.05))
    Rt = Rb @ Rz(p.t_yaw) @ Rx(p.lean) @ Ry(p.t_roll)
    poser('torse', base_t, Rt)
    cou = base_t + Rt @ Vector((0, 0, COU_Z - HANCHE_Z - 0.05))
    Rh = Rt @ Rz(p.h_yaw) @ Rx(p.h_pitch) @ Ry(p.h_roll)
    poser('tete', cou, Rh)
    info = {'Rt': Rt, 'Rh': Rh, 'cou': cou}
    bas = Vector((0, 0, -1))
    for s, c in ((1, 'L'), (-1, 'R')):
        S = base_t + Rt @ Vector((s * EP_X, 0, EPAULE_Z - HANCHE_Z - 0.05 + p.epaule_dz))
        T = p.mains.get(s, S + V(s * 0.035, 0.0, -0.255))
        pole = p.coudes.get(s, S + V(s * 0.25, -0.35, -0.1))
        E, W = ik2(S, T, L_BRAS, L_AVBRAS, pole)
        poser('bras.' + c, S, bas.rotation_difference((E - S).normalized()).to_matrix())
        Rf = bas.rotation_difference((W - E).normalized()).to_matrix()
        poser('avbras.' + c, E, Rf); poser('main.' + c, W, Rf)
        info['main' + c] = W + (W - E).normalized() * 0.03
        H = p.bassin + Rb @ Vector((s * HA_X, 0, 0))
        A = p.pieds.get(s, V(s * 0.066, 0, CHEVILLE_Z))
        pk = p.genoux.get(s, H + V(s * 0.04, 0.6, -0.05))
        K, A2 = ik2(H, A, L_CUISSE, L_TIBIA, pk)
        poser('cuisse.' + c, H, bas.rotation_difference((K - H).normalized()).to_matrix())
        poser('tibia.' + c, K, bas.rotation_difference((A2 - K).normalized()).to_matrix())
        poser('pied.' + c, A2, Rz(p.b_yaw * 0.5) @ Rx(p.pied_pitch.get(s, 0)))
    for nom, e in OBJETS.items():
        if nom in p.objets:
            e.matrix_basis = p.objets[nom]; e.hide_render = False
            for ch in e.children: ch.hide_render = False
        else:
            e.hide_render = True
            for ch in e.children: ch.hide_render = True
    return info

# --------- outils de pose
def ease(t): return t * t * (3 - 2 * t)
def mix(a, b, t): return a + (b - a) * t
def epaule(p, s):
    Rb = Rz(p.b_yaw) @ Rx(p.b_pitch) @ Ry(p.b_roll)
    base_t = p.bassin + Rb @ Vector((0, 0, 0.05))
    Rt = Rb @ Rz(p.t_yaw) @ Rx(p.lean) @ Ry(p.t_roll)
    return base_t + Rt @ Vector((s * EP_X, 0, EPAULE_Z - HANCHE_Z - 0.05 + p.epaule_dz))
def tete_centre(p):
    Rb = Rz(p.b_yaw) @ Rx(p.b_pitch) @ Ry(p.b_roll)
    base_t = p.bassin + Rb @ Vector((0, 0, 0.05))
    Rt = Rb @ Rz(p.t_yaw) @ Rx(p.lean) @ Ry(p.t_roll)
    cou = base_t + Rt @ Vector((0, 0, COU_Z - HANCHE_Z - 0.05))
    Rh = Rt @ Rz(p.h_yaw) @ Rx(p.h_pitch) @ Ry(p.h_roll)
    return cou + Rh @ Vector((0, 0, TETE_C - COU_Z)), Rh

def assis(p, siege_z=0.36):
    dz = siege_z - 0.36
    p.bassin = V(0, -0.02, 0.41 + dz)
    for s in (1, -1):
        H = p.bassin + V(s * HA_X, 0, 0)
        p.pieds[s] = H + V(s * 0.008, 0.199, -0.145)
        p.genoux[s] = H + V(s * 0.02, 0.5, 0.4)
        p.pied_pitch[s] = 0.35

def tasse_a(p, main_pos, s, incl=0.0):
    """Tasse tenue par l'anse dans la main du côté s (incl : inclinaison vers la bouche)."""
    c = main_pos + V(-s * 0.048, 0.012, 0.0)
    R = Rx(-incl) @ Rz(math.radians(180 if s > 0 else 0) + 0.0)
    return Matrix.Translation(c) @ R.to_4x4()

CLAVIER = V(0, 0.30, 0.69)       # centre du clavier (repère perso), surface du bureau à 0,68

# --------- animations
def a_repos(f, n):
    p = Pose(); ph = 2 * math.pi * f / n; r = math.sin(ph)
    p.bassin = V(0, 0, H0 - 0.006 + 0.002 * r); p.epaule_dz = 0.006 * r; p.lean = -0.012 * r; p.h_pitch = 0.03 - 0.025 * r
    for s in (1, -1): p.mains[s] = epaule(p, s) + V(s * 0.038, 0.012, -0.255)
    return p

PAS = 0.09    # demi-amplitude du pas (unités)
def a_marche(f, n):
    p = Pose(); u = f / n; ph = 2 * math.pi * u
    p.bassin = V(0, 0, H0 - 0.016 + 0.011 * math.sin(ph) ** 2)
    p.b_yaw = -0.10 * math.cos(ph); p.t_yaw = 0.16 * math.cos(ph); p.lean = 0.07; p.h_pitch = -0.02
    p.t_roll = 0.025 * math.sin(2 * ph)
    for s, dec in ((1, 0.0), (-1, 0.5)):
        q = (u + dec) % 1.0
        if q < 0.5:
            fo = PAS * (1 - 4 * q); z = 0; pit = 0.0 if q < 0.35 else -0.0 + 0.5 * (q - 0.35) / 0.15
        else:
            w = (q - 0.5) * 2; fo = -PAS + 2 * PAS * ease(w); z = 0.065 * math.sin(math.pi * w); pit = 0.5 * (1 - w) - 0.25 * math.sin(math.pi * w) * 0 - 0.2 * max(0, w - 0.6) / 0.4
        p.pieds[s] = V(s * 0.066, fo, CHEVILLE_Z + z); p.pied_pitch[s] = pit if q >= 0.35 else 0.0
        p.genoux[s] = V(s * 0.07, 0.6, 0.35)
    for s in (1, -1):
        sw = -s * 0.085 * math.cos(ph)
        p.mains[s] = epaule(p, s) + V(s * 0.045, sw, -0.25)
        p.coudes[s] = epaule(p, s) + V(s * 0.25, -0.35 + sw, -0.1)
    return p

def a_tape(f, n):
    p = Pose(); assis(p); ph = 2 * math.pi * f / n
    p.lean = 0.28; p.h_pitch = 0.0 + 0.015 * math.sin(ph)
    for s in (1, -1):
        tap = max(0.0, math.sin(ph + (0 if s > 0 else math.pi)))
        p.mains[s] = CLAVIER + V(s * 0.075 + s * 0.012 * math.sin(ph * 0.5 + s), -0.03, 0.012 + 0.016 * tap)
        p.coudes[s] = epaule(p, s) + V(s * 0.35, -0.15, -0.35)
    return p

T_BOIT = [0.0, 0.45, 1.0, 1.0, 0.55, 0.12]
def a_assis_boit(f, n):
    p = Pose(); assis(p); t = ease(T_BOIT[f])
    p.lean = mix(0.26, 0.04, t); p.h_pitch = mix(0.04, -0.30, t)
    p.mains[1] = CLAVIER + V(0.075, -0.03, 0.012)
    p.coudes[1] = epaule(p, 1) + V(0.35, -0.15, -0.35)
    bas_ = CLAVIER + V(-0.17, -0.07, 0.03)
    tc, Rh = tete_centre(p)
    bouche = tc + Rh @ V(-0.015, 0.215, -0.06)
    m = Vector([mix(a, b, t) for a, b in zip(bas_, bouche + V(-0.048, 0.0, -0.01))])
    p.mains[-1] = m; p.coudes[-1] = epaule(p, -1) + V(-0.35, -0.1, -0.3)
    p.objets['tasse'] = tasse_a(p, m + V(0, 0, 0), -1, incl=1.1 * t)
    return p

def a_cafe(f, n):
    p = Pose(); t = ease(T_BOIT[f]); r = math.sin(2 * math.pi * f / n)
    p.bassin = V(0, 0, H0 - 0.006 + 0.002 * r); p.h_pitch = mix(0.06, -0.30, t); p.lean = mix(0.02, -0.04, t)
    p.mains[1] = epaule(p, 1) + V(0.038, 0.012, -0.255)
    tc, Rh = tete_centre(p)
    bouche = tc + Rh @ V(-0.015, 0.215, -0.06)
    bas_ = epaule(p, -1) + V(0.02, 0.17, -0.16)
    m = Vector([mix(a, b, t) for a, b in zip(bas_, bouche + V(-0.048, 0.0, -0.01))])
    p.mains[-1] = m; p.coudes[-1] = epaule(p, -1) + V(-0.3, -0.25, -0.3)
    p.objets['tasse'] = tasse_a(p, m, -1, incl=1.1 * t)
    return p

def a_parle(f, n):
    p = Pose(); ph = 2 * math.pi * f / n
    p.t_yaw = 0.06 * math.sin(ph); p.h_pitch = 0.04 * math.sin(2 * ph) - 0.02; p.h_yaw = -0.08 * math.sin(ph); p.lean = 0.02
    p.mains[-1] = epaule(p, -1) + V(-0.06 + 0.03 * math.sin(ph), 0.16 + 0.03 * math.cos(ph), -0.14 + 0.06 * math.sin(ph))
    p.mains[1] = epaule(p, 1) + V(0.07 - 0.02 * math.sin(ph + 2), 0.12 + 0.03 * math.sin(ph + 1), -0.17 + 0.05 * math.sin(ph + 2.2))
    for s in (1, -1): p.coudes[s] = epaule(p, s) + V(s * 0.35, -0.2, -0.3)
    return p

def a_joie(f, n):
    p = Pose(); ph = 2 * math.pi * f / n
    saut = [0.0, 0.035, 0.055, 0.03][f]; acc = [0.025, 0.0, 0.0, 0.005][f]
    p.bassin = V(0, 0, H0 - 0.006 - acc + saut); p.h_pitch = -0.18; p.lean = -0.04
    for s in (1, -1):
        p.pieds[s] = V(s * 0.07, 0, CHEVILLE_Z + saut * 0.9); p.pied_pitch[s] = 0.3 * (saut > 0.01)
        p.mains[s] = epaule(p, s) + V(s * (0.12 + 0.02 * math.sin(ph + (0 if s > 0 else math.pi))), 0.02, 0.24 + 0.025 * math.sin(ph + (0 if s > 0 else math.pi)))
        p.coudes[s] = epaule(p, s) + V(s * 0.5, -0.05, 0.05)
    return p

def a_gratte(f, n):
    p = Pose(); ph = 2 * math.pi * f / n
    p.h_roll = 0.16; p.h_pitch = 0.06; p.t_roll = 0.06; p.epaule_dz = 0.015
    tc, Rh = tete_centre(p)
    p.mains[-1] = tc + Rh @ V(-0.17, -0.01 + 0.025 * math.sin(ph), 0.0 + 0.02 * math.cos(ph))
    p.coudes[-1] = epaule(p, -1) + V(-0.5, 0.05, 0.25)
    p.mains[1] = epaule(p, 1) + V(0.04, 0.0, -0.255)
    return p

def a_sautille(f, n):
    p = Pose(); ph = 2 * math.pi * f / n
    saut = [0.0, 0.05, 0.10, 0.085, 0.035, 0.0][f]; acc = [0.04, 0.01, 0.0, 0.0, 0.005, 0.03][f]
    p.bassin = V(0, 0, H0 - 0.006 - acc + saut); p.lean = 0.05 + acc; p.h_pitch = -0.06
    for s in (1, -1):
        p.pieds[s] = V(s * 0.07, 0.01, CHEVILLE_Z + saut * 0.92); p.pied_pitch[s] = 0.45 * min(1, saut / 0.05)
        lev = min(1.0, saut / 0.08)
        p.mains[s] = epaule(p, s) + V(s * mix(0.05, 0.1, lev), mix(-0.04, 0.1, lev), mix(-0.23, 0.1, lev))
        p.coudes[s] = epaule(p, s) + V(s * 0.45, -0.25, -0.1)
    return p

def a_cloche(f, n):
    p = Pose(); ph = 2 * math.pi * f / n
    p.bassin = V(0, 0, H0 - 0.01 + 0.006 * abs(math.sin(ph))); p.h_roll = -0.06; p.h_pitch = -0.05; p.t_roll = 0.03
    m = epaule(p, -1) + V(-0.12 + 0.02 * math.sin(ph), 0.1, 0.2)
    p.mains[-1] = m; p.coudes[-1] = epaule(p, -1) + V(-0.5, -0.05, 0.0)
    p.mains[1] = p.bassin + V(0.14, -0.005, 0.075); p.coudes[1] = epaule(p, 1) + V(0.6, -0.1, -0.1)
    p.objets['cloche'] = Matrix.Translation(m + V(0, 0, -0.005)) @ (Ry(0.55 * math.sin(ph))).to_4x4()
    return p

SIEGE_CANAPE = 0.42
def a_manette(f, n):
    p = Pose(); assis(p, SIEGE_CANAPE); ph = 2 * math.pi * f / n
    p.lean = -0.06; p.t_roll = 0.05 * math.sin(ph); p.h_pitch = 0.08; p.h_roll = -0.03 * math.sin(ph)
    c = p.bassin + V(0.0 + 0.01 * math.sin(ph), 0.2, 0.2 + 0.006 * math.cos(ph))
    for s in (1, -1):
        p.mains[s] = c + V(s * 0.065, -0.012, -0.005)
        p.coudes[s] = epaule(p, s) + V(s * 0.3, -0.2, -0.35)
    p.objets['manette'] = Matrix.Translation(c + V(0, 0, 0.005)) @ (Ry(0.12 * math.sin(ph)) @ Rx(-0.55)).to_4x4()
    return p

ANIMS = {   # nom : (fonction, images, fps, assis, siège z)
    'marche': (a_marche, 8, 12, False, None),
    'repos': (a_repos, 4, 3, False, None),
    'tape': (a_tape, 4, 8, True, 0.36),
    'assis_boit': (a_assis_boit, 6, 5, True, 0.36),
    'cafe_debout': (a_cafe, 6, 5, False, None),
    'parle': (a_parle, 6, 6, False, None),
    'joie': (a_joie, 4, 6, False, None),
    'gratte': (a_gratte, 4, 8, False, None),
    'sautille': (a_sautille, 6, 10, False, None),
    'cloche': (a_cloche, 6, 10, False, None),
    'manette': (a_manette, 4, 4, True, SIEGE_CANAPE),
}
DIRS = ['SE_fd', 'S', 'SO_fg', 'O', 'NO_dg', 'N', 'NE_dd', 'E']   # direction k : angle studio k×45°

# ------------------------------------------------------------------------------------------
# Compositeur : sorties PNG base + masques
# ------------------------------------------------------------------------------------------
sc.use_nodes = True
tree = sc.node_tree; tree.nodes.clear()
rl = tree.nodes.new('CompositorNodeRLayers')
comp = tree.nodes.new('CompositorNodeComposite'); tree.links.new(rl.outputs['Image'], comp.inputs['Image'])
fo = tree.nodes.new('CompositorNodeOutputFile'); fo.base_path = SORTIE
fo.format.file_format = 'PNG'; fo.format.color_mode = 'RGBA'; fo.format.color_depth = '8'
fo.file_slots.clear()
for n in ('base', 'mA', 'mB'): fo.file_slots.new(n)
tree.links.new(rl.outputs['Image'], fo.inputs['base'])
tree.links.new(rl.outputs['mA'], fo.inputs['mA'])
tree.links.new(rl.outputs['mB'], fo.inputs['mB'])
for i in (1, 2):
    sl = fo.file_slots[i]
    try: sl.use_node_format = True; sl.save_as_render = False
    except Exception as e: print('save_as_render ?', e)

LC = {c.name: c for c in vl.layer_collection.children}
def couches(actif):
    """actif = None (corps) ou nom d'accessoire."""
    LC['Corps'].holdout = actif is not None
    LC['Objets'].holdout = actif is not None
    for a in ACCS:
        LC['Acc_' + a].exclude = (a != actif)

def chemins(anim, couche, f, d, slots):
    for i, n in enumerate(('base', 'mA', 'mB')):
        fo.file_slots[i].path = '%s/%s/f%02dd%d_%s_' % (anim, couche, f, d, n) if n in slots else '_jeter/%s_' % n

def projeter(pt):
    co = world_to_camera_view(sc, cam, pt)
    return [round(co.x * RES, 2), round((1 - co.y) * RES, 2)]

# ------------------------------------------------------------------------------------------
# Rendu
# ------------------------------------------------------------------------------------------
def rendre(liste, accs):
    os.makedirs(SORTIE, exist_ok=True)
    ancres_f = os.path.join(SORTIE, 'ancres.json')
    ancres = json.load(open(ancres_f, encoding='utf-8')) if os.path.exists(ancres_f) else {}
    t0 = time.time(); nb = 0
    for anim, f, d in liste:
        fn, n, fps, ass, sz = ANIMS[anim]
        p = fn(f, n)
        theta = math.radians(90 - 45 * d)
        arm.rotation_euler = (0, 0, theta)
        info = appliquer(p)
        vl.update()
        M = arm.matrix_world
        tc, Rh = tete_centre(p)
        a = {
            'tete': projeter(M @ (tc + Rh @ Vector((0, 0, 0.19)))),
            'mainD': projeter(M @ info['mainR']), 'mainG': projeter(M @ info['mainL']),
        }
        ancres.setdefault(anim, {}).setdefault(str(f), {})[str(d)] = a
        couches(None); chemins(anim, 'corps', f, d, ('base', 'mA', 'mB'))
        bpy.ops.render.render(write_still=False); nb += 1
        for ac in accs:
            couches(ac); chemins(anim, ac, f, d, ('base', 'mB'))
            bpy.ops.render.render(write_still=False); nb += 1
        if nb % 40 < 1 + len(accs):
            print('[rendu] %s f%d d%d  %d rendus  %.1fs' % (anim, f, d, nb, time.time() - t0), flush=True)
    # ancres communes
    commun = {'pieds': list(ANCRE_PIEDS), 'res': RES, 'facteur_px_studio': FACTEUR}
    kb = {}
    for d in range(8):
        arm.rotation_euler = (0, 0, math.radians(90 - 45 * d)); vl.update()
        kb[str(d)] = {'clavier': projeter(arm.matrix_world @ CLAVIER)}
    commun['clavier_par_direction'] = kb
    commun['clavier_local'] = {'avant': 0.30, 'z': 0.69}
    commun['siege_z'] = {k: v[4] for k, v in ANIMS.items() if v[3]}
    ancres['_commun'] = commun
    json.dump(ancres, open(ancres_f, 'w', encoding='utf-8'), ensure_ascii=False)
    print('[rendu] fini : %d rendus en %.1fs' % (nb, time.time() - t0), flush=True)

if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)

anims_sel = arg('--anims', None)
accs_sel = arg('--acc', None)
accs = ACCS if accs_sel in (None, True) else [a for a in accs_sel.split(',') if a]
if accs_sel == 'aucun': accs = []
if TEST:
    liste = [('repos', 0, d) for d in range(8)] + [('tape', 1, 0), ('tape', 1, 6), ('tape', 1, 2), ('marche', 1, 1), ('marche', 3, 7),
             ('assis_boit', 2, 1), ('cafe_debout', 2, 0), ('joie', 2, 1), ('gratte', 1, 1), ('cloche', 1, 1), ('manette', 1, 6), ('sautille', 2, 1), ('parle', 1, 7)]
else:
    noms = list(ANIMS) if anims_sel in (None, True) else anims_sel.split(',')
    liste = [(a, f, d) for a in noms for f in range(ANIMS[a][1]) for d in range(8)]
rendre(liste, accs)
