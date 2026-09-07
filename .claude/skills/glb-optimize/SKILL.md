---
name: glb-optimize
description: Web-optimise a GLB model (usually a Meshy scan) for the art pages using the garden recipe - meshopt compression, quantisation, 1024px webp textures, tangents stripped, no decimation. Use when the user wants to shrink a GLB, prepare a model for a new piece, or bring a Meshy export into static/art/.
---

# GLB optimisation recipe

The standard pipeline for getting a large GLB (typically a 50-150 MB
Meshy photogrammetry export) down to a web-shippable size without
losing any geometry. This is the recipe garden.html's flowers and
fino's bust went through. Typical result: 85-90% smaller.

**Never decimate/simplify.** Simplification tears these scan meshes
(see memory: glb-no-aggressive-simplify). The full vertex count always
survives; the wins come from quantisation, meshopt, and texture
compression alone.

## Tools

`gltf-transform` CLI is installed via Homebrew (`/opt/homebrew/bin/gltf-transform`,
v4.x). Its bundled libraries live at
`/opt/homebrew/lib/node_modules/@gltf-transform/cli/node_modules/@gltf-transform/*`
(entry point `dist/index.modern.js`) and can be imported directly by a
node script for steps the CLI has no flag for. No Blender; don't
suggest it.

## Steps

1. **Inspect first.** `gltf-transform inspect <in.glb>` and note:
   vertex count (to verify it survives), which attributes exist
   (TANGENT? NORMAL? TEXCOORD?), textures and their slots, materials.
   A Meshy export is sometimes bare POSITION-only geometry with no
   materials; that changes step 2 and 3 and the page will need
   `computeVertexNormals()` or a matcap/normal material. Flag this to
   the user.

2. **Strip tangents, if present.** three.js regenerates tangents from
   the normal map, so they are dead weight (16 bytes/vertex). The CLI
   has no flag for it; use a scratchpad node script:

   ```js
   import { NodeIO } from '/opt/homebrew/lib/node_modules/@gltf-transform/cli/node_modules/@gltf-transform/core/dist/index.modern.js';
   const [,, inPath, outPath] = process.argv;
   const io = new NodeIO();
   const doc = await io.read(inPath);
   for (const mesh of doc.getRoot().listMeshes())
     for (const prim of mesh.listPrimitives()) {
       const t = prim.getAttribute('TANGENT');
       if (t) { prim.setAttribute('TANGENT', null); t.dispose(); }
     }
   await io.write(outPath, doc);
   ```

3. **Optimise.** Textured model:

   ```
   gltf-transform optimize in.glb out.glb --compress meshopt \
     --texture-compress webp --texture-size 1024 --simplify false
   ```

   Untextured model: drop the two texture flags. `--simplify false` is
   the load-bearing flag; never omit it.

4. **Verify.** `gltf-transform inspect out.glb` again: vertex count
   unchanged, `extensionsRequired` now lists `EXT_meshopt_compression`
   and `KHR_mesh_quantization` (plus `EXT_texture_webp` if textured),
   textures at 1024px webp. Report before/after sizes.

5. **Place it.** Output goes in the piece's asset folder under
   `static/art/` (e.g. `static/art/fino/`, `static/art/garden-assets/`).
   Don't touch `public/`; it's gitignored and rebuilt by Hugo.

## Loading on the page

The page must decode meshopt or the model won't load:

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);
```

with the site's standard import map (three@0.160 on jsdelivr, plus the
`three/addons/` mapping); garden.html and fino.html are the reference
implementations.
