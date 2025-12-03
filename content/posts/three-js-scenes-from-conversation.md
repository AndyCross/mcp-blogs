+++
title = "Rendering Conversational 3D Scenes with Three.js and MCP"
date = "2024-12-02"
draft = false
tags = ["mcp", "ai", "threejs", "webgl", "python"]
+++

In my [previous post](/posts/building-3d-scenes-with-mcp/), I promised that the scene data was portable—that you could feed it to "a game engine, a GIS tool, a mapping API, whatever." Time to make good on that.

This post walks through building a Three.js web viewer that consumes scene data from the MCP server in real-time. You'll end up with a browser-based 3D view that updates live as Claude manipulates the scene through conversation.

## The Three-Layer Architecture

Here's what we're building:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
│  ┌─────────────────┐       ┌─────────────────────────────────┐  │
│  │   Chat UI       │       │      Three.js Viewer            │  │
│  │                 │       │                                 │  │
│  │  User: "Add a   │       │     ┌───┐                       │  │
│  │  windmill to    │       │     │ ▲ │  ← Windmill           │  │
│  │  the north"     │       │     └───┘                       │  │
│  │                 │       │           ┌─────┐               │  │
│  │  Claude: "Done, │       │           │     │ ← House       │  │
│  │  I've placed..."│       │           └─────┘               │  │
│  └────────┬────────┘       └──────────────▲──────────────────┘  │
│           │                               │                      │
│           │ Anthropic API                 │ Poll/SSE             │
│           │ (streaming)                   │                      │
└───────────┼───────────────────────────────┼──────────────────────┘
            │                               │
            ▼                               │
┌───────────────────────┐                   │
│        Claude         │                   │
│                       │                   │
│  Interprets natural   │                   │
│  language, calls      │                   │
│  MCP tools            │                   │
└───────────┬───────────┘                   │
            │                               │
            │ MCP Protocol                  │
            │ (tool calls)                  │
            ▼                               │
┌───────────────────────────────────────────┴───────────────────┐
│                    Scene MCP Server                            │
│                                                                │
│  • Stores objects with WGS84 coordinates                       │
│  • Handles geocoding and geodesic math                         │
│  • HTTP/SSE transport for web clients                          │
└────────────────────────────────────────────────────────────────┘
```

The separation of concerns is clean:

| Layer | Responsibility |
|-------|----------------|
| **MCP Server** | Ground truth for scene state. Precise coordinates, geodesic calculations. |
| **Claude** | Natural language interpretation. Turns "behind the house" into bearings and distances. |
| **Three.js** | Rendering only. Consumes scene data, draws geometry. No business logic. |

The viewer doesn't need to understand spatial relationships. It just draws what the server tells it to draw.

## Running the MCP Server in HTTP Mode

The scene server supports HTTP transport out of the box. Instead of stdio (which Claude Desktop uses), we'll run it as a web service:

```bash
SCENE_MCP_TRANSPORT=http SCENE_MCP_PORT=8080 scene-mcp
```

This starts an HTTP server on port 8080 that speaks the MCP protocol. Under the hood, FastMCP uses Server-Sent Events (SSE) for the transport—the client opens a persistent connection to `/sse`, and the server streams responses back.

For CORS during local development, you might need to add headers. Here's a quick modification if you're hacking on the server:

```python
# In main.py, if you need CORS for local dev
scene_mcp.run(
    transport="sse",
    host="0.0.0.0",
    port=8080,
)
```

FastMCP handles the SSE plumbing. Your client just needs to POST tool calls and listen for responses.

## Building the Three.js Viewer

Now for the fun part. We need a viewer that:

1. Fetches scene data from the MCP server
2. Transforms WGS84 coordinates into 3D world space
3. Creates geometry based on object types
4. Updates in real-time as the scene changes

### The Coordinate Problem

Here's the first interesting challenge. The MCP server stores positions in WGS84—latitude and longitude on a sphere. Three.js works in Cartesian coordinates—X, Y, Z in a flat 3D space.

For a local scene (say, a village or a farm), we can use a simple approximation: pick a reference point (the first object, or a configured origin), and project everything else relative to it using a local tangent plane.

The math isn't scary:

```javascript
// Reference point (first object becomes origin)
let originLat = null;
let originLon = null;

// Approximate meters per degree at a given latitude
function metersPerDegree(lat) {
    const latRad = lat * Math.PI / 180;
    return {
        lat: 111132.92 - 559.82 * Math.cos(2 * latRad) + 1.175 * Math.cos(4 * latRad),
        lon: 111412.84 * Math.cos(latRad) - 93.5 * Math.cos(3 * latRad)
    };
}

// Convert WGS84 to local Three.js coordinates
function geoToLocal(lat, lon, elevation) {
    if (originLat === null) {
        originLat = lat;
        originLon = lon;
    }
    
    const scale = metersPerDegree(originLat);
    
    return {
        x: (lon - originLon) * scale.lon,
        y: elevation,
        z: -(lat - originLat) * scale.lat  // Negative because lat increases northward
    };
}
```

This gives us meter-scale accuracy within a few kilometers of the origin—more than enough for our purposes. For planetary-scale scenes, you'd want a proper geodetic library, but let's not over-engineer.

### Object Geometry

The MCP server stores freeform `type` strings. The viewer needs to turn those into 3D shapes. Here's a simple mapping:

```javascript
function createGeometryForType(type) {
    const geometries = {
        'house': () => new THREE.BoxGeometry(10, 8, 12),
        'shed': () => new THREE.BoxGeometry(4, 3, 5),
        'tree': () => new THREE.ConeGeometry(3, 8, 8),
        'windmill': () => new THREE.CylinderGeometry(1, 2, 15, 8),
        'barn': () => new THREE.BoxGeometry(15, 10, 20),
        'church': () => new THREE.BoxGeometry(12, 20, 25),
        'pond': () => new THREE.CircleGeometry(8, 32),
    };
    
    const factory = geometries[type.toLowerCase()];
    if (factory) return factory();
    
    // Default: a simple sphere for unknown types
    return new THREE.SphereGeometry(3, 16, 16);
}

function createMaterialForType(type) {
    const colors = {
        'house': 0xc9302c,      // Warm red
        'shed': 0x8b4513,       // Brown
        'tree': 0x228b22,       // Forest green
        'windmill': 0xf5f5f5,   // Off-white
        'barn': 0x8b0000,       // Dark red
        'church': 0x808080,     // Gray stone
        'pond': 0x4169e1,       // Royal blue
    };
    
    const color = colors[type.toLowerCase()] || 0x9932cc;  // Default: purple
    return new THREE.MeshLambertMaterial({ color });
}
```

### Scene Synchronization

We need to keep the Three.js scene in sync with the MCP server's state. The simplest approach: poll `get_scene` periodically and diff against what we're currently rendering.

The MCP protocol uses JSON-RPC over SSE, so you'll need an MCP client library or a thin wrapper. For this example, I'll show the logic assuming you have a `callTool` function that handles the protocol details:

```javascript
class SceneSync {
    constructor(scene, mcpClient) {
        this.scene = scene;
        this.mcpClient = mcpClient;
        this.objects = new Map();  // name -> Three.js mesh
    }
    
    async fetchScene() {
        // Call the get_scene tool via MCP
        // The mcpClient handles the JSON-RPC/SSE protocol
        const result = await this.mcpClient.callTool('get_scene', {});
        return result.objects || [];
    }
    
    sync(serverObjects) {
        const serverNames = new Set(serverObjects.map(o => o.name));
        
        // Remove objects that no longer exist
        for (const [name, mesh] of this.objects) {
            if (!serverNames.has(name)) {
                this.scene.remove(mesh);
                this.objects.delete(name);
            }
        }
        
        // Add or update objects
        for (const obj of serverObjects) {
            if (this.objects.has(obj.name)) {
                // Update existing
                this.updateObject(obj);
            } else {
                // Create new
                this.createObject(obj);
            }
        }
    }
    
    createObject(obj) {
        const geometry = createGeometryForType(obj.type);
        const material = createMaterialForType(obj.type);
        const mesh = new THREE.Mesh(geometry, material);
        
        const pos = geoToLocal(obj.lat, obj.lon, obj.elevation);
        mesh.position.set(pos.x, pos.y, pos.z);
        mesh.rotation.y = -obj.orientation * Math.PI / 180;  // Convert to radians
        mesh.scale.setScalar(obj.scale);
        
        mesh.userData = { name: obj.name, type: obj.type };
        
        this.scene.add(mesh);
        this.objects.set(obj.name, mesh);
    }
    
    updateObject(obj) {
        const mesh = this.objects.get(obj.name);
        if (!mesh) return;
        
        const pos = geoToLocal(obj.lat, obj.lon, obj.elevation);
        mesh.position.set(pos.x, pos.y, pos.z);
        mesh.rotation.y = -obj.orientation * Math.PI / 180;
        mesh.scale.setScalar(obj.scale);
    }
}
```

## Connecting Claude to the Loop

For the chat interface, you'll use the Anthropic API with MCP tool definitions. The flow is:

1. User types a message
2. Send to Claude with the MCP tools available
3. Claude streams back, potentially calling tools
4. Tool calls go to the MCP server
5. Results return to Claude
6. Claude generates a natural language response
7. Meanwhile, the viewer polls and updates

Here's the skeleton for the Claude integration:

```javascript
async function chat(userMessage, conversationHistory) {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
            model: 'claude-sonnet-4-20250514',
            max_tokens: 1024,
            system: `You are a 3D scene builder. You have access to tools for placing 
                     and manipulating objects in geographic space. When the user 
                     describes locations, use geocode to find coordinates. When they 
                     use relative terms like "behind" or "near", calculate appropriate 
                     positions using the object's orientation and calculate_offset.`,
            messages: conversationHistory,
            tools: MCP_TOOL_DEFINITIONS,  // Your tool schemas
            stream: true
        })
    });
    
    // Handle streaming response with tool calls...
}
```

The key insight: Claude handles all the spatial reasoning. When someone says "put a shed behind the farmhouse," Claude:

1. Calls `get_object("Farmhouse")` to get its position and orientation
2. Reasons that "behind" means opposite the facing direction
3. Calls `calculate_offset` with the appropriate bearing and a reasonable distance
4. Calls `add_object` with the computed coordinates

Your viewer doesn't need to understand any of this. It just renders whatever's in the scene.

## The Complete Viewer

Here's a self-contained HTML file that demonstrates the rendering side. This version includes a demo mode that simulates scene data, so you can see it working immediately. To connect to a real MCP server, you'd replace the mock `fetchScene` with actual MCP client calls:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Scene Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'JetBrains Mono', monospace;
            background: #1a1a2e; 
            overflow: hidden;
        }
        #container { width: 100vw; height: 100vh; }
        #info {
            position: absolute;
            top: 20px;
            left: 20px;
            color: #eee;
            background: rgba(0,0,0,0.7);
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 14px;
            max-width: 300px;
        }
        #info h3 { margin-bottom: 10px; color: #00d4ff; }
        #object-list { 
            list-style: none; 
            max-height: 200px; 
            overflow-y: auto;
        }
        #object-list li { 
            padding: 4px 0; 
            border-bottom: 1px solid #333;
        }
        #controls {
            position: absolute;
            bottom: 20px;
            left: 20px;
            display: flex;
            gap: 10px;
        }
        #controls button {
            background: #00d4ff;
            border: none;
            color: #1a1a2e;
            padding: 10px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-family: inherit;
            font-weight: bold;
        }
        #controls button:hover { background: #00b8e6; }
        #status {
            position: absolute;
            bottom: 60px;
            left: 20px;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div id="container"></div>
    <div id="info">
        <h3>Scene Objects</h3>
        <ul id="object-list"><li>Click "Add Objects" to populate</li></ul>
    </div>
    <div id="status">Demo mode - simulating MCP server</div>
    <div id="controls">
        <button onclick="addDemoObjects()">Add Objects</button>
        <button onclick="clearScene()">Clear</button>
    </div>
    
    <script type="importmap">
    {
        "imports": {
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
        }
    }
    </script>
    
    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
        
        // Simulated scene data (would come from MCP server)
        let mockSceneData = [];
        
        // Coordinate transformation
        let originLat = null, originLon = null;
        
        function metersPerDegree(lat) {
            const latRad = lat * Math.PI / 180;
            return {
                lat: 111132.92 - 559.82 * Math.cos(2 * latRad),
                lon: 111412.84 * Math.cos(latRad)
            };
        }
        
        function geoToLocal(lat, lon, elevation = 0) {
            if (originLat === null) {
                originLat = lat;
                originLon = lon;
            }
            const scale = metersPerDegree(originLat);
            return new THREE.Vector3(
                (lon - originLon) * scale.lon,
                elevation,
                -(lat - originLat) * scale.lat
            );
        }
        
        // Geometry factories
        function createMesh(type) {
            const configs = {
                house:    { geo: new THREE.BoxGeometry(10, 8, 12), color: 0xc9302c },
                shed:     { geo: new THREE.BoxGeometry(4, 3, 5), color: 0x8b4513 },
                tree:     { geo: new THREE.ConeGeometry(3, 10, 8), color: 0x228b22 },
                windmill: { geo: new THREE.CylinderGeometry(1, 2, 15, 8), color: 0xf5f5f5 },
                barn:     { geo: new THREE.BoxGeometry(15, 10, 20), color: 0x8b0000 },
                church:   { geo: new THREE.BoxGeometry(12, 20, 25), color: 0x708090 },
                pond:     { geo: new THREE.CircleGeometry(8, 32).rotateX(-Math.PI/2), color: 0x4169e1 },
                farmhouse:{ geo: new THREE.BoxGeometry(12, 9, 14), color: 0xdaa520 },
            };
            
            const cfg = configs[type.toLowerCase()] || { 
                geo: new THREE.SphereGeometry(3, 16, 16), 
                color: 0x9932cc 
            };
            
            return new THREE.Mesh(
                cfg.geo,
                new THREE.MeshLambertMaterial({ color: cfg.color })
            );
        }
        
        // Three.js setup
        const container = document.getElementById('container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1a1a2e);
        
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        camera.position.set(50, 80, 100);
        
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);
        
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        
        // Lighting
        scene.add(new THREE.AmbientLight(0x404040, 2));
        const sun = new THREE.DirectionalLight(0xffffff, 1.5);
        sun.position.set(50, 100, 50);
        scene.add(sun);
        
        // Ground plane
        const ground = new THREE.Mesh(
            new THREE.PlaneGeometry(1000, 1000),
            new THREE.MeshLambertMaterial({ color: 0x3d5c3d })
        );
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -0.1;
        scene.add(ground);
        
        // Grid helper
        const grid = new THREE.GridHelper(200, 20, 0x444444, 0x333333);
        scene.add(grid);
        
        // Scene object tracking
        const sceneObjects = new Map();
        
        function syncScene(serverObjects) {
            const serverNames = new Set(serverObjects.map(o => o.name));
            
            // Remove deleted objects
            for (const [name, mesh] of sceneObjects) {
                if (!serverNames.has(name)) {
                    scene.remove(mesh);
                    sceneObjects.delete(name);
                }
            }
            
            // Add or update objects
            for (const obj of serverObjects) {
                let mesh = sceneObjects.get(obj.name);
                
                if (!mesh) {
                    mesh = createMesh(obj.type);
                    mesh.userData = { name: obj.name, type: obj.type };
                    scene.add(mesh);
                    sceneObjects.set(obj.name, mesh);
                }
                
                const pos = geoToLocal(obj.lat, obj.lon, obj.elevation);
                mesh.position.copy(pos);
                
                // Offset geometry to sit on ground
                if (obj.type.toLowerCase() !== 'pond') {
                    mesh.position.y += mesh.geometry.parameters?.height / 2 || 0;
                }
                
                mesh.rotation.y = -obj.orientation * Math.PI / 180;
                mesh.scale.setScalar(obj.scale);
            }
            
            // Update UI
            updateObjectList(serverObjects);
        }
        
        function updateObjectList(objects) {
            const list = document.getElementById('object-list');
            if (objects.length === 0) {
                list.innerHTML = '<li>No objects in scene</li>';
                return;
            }
            list.innerHTML = objects.map(o => 
                `<li><strong>${o.name}</strong> (${o.type})</li>`
            ).join('');
        }
        
        // Demo functions (simulating what MCP server would provide)
        window.addDemoObjects = function() {
            // Reset origin for fresh scene
            originLat = null;
            originLon = null;
            
            // Sample scene data - this is what get_scene() returns from the MCP server
            mockSceneData = [
                { name: "Farmhouse", type: "farmhouse", lat: 52.1234, lon: -0.5678, elevation: 0, orientation: 180, scale: 1 },
                { name: "Barn", type: "barn", lat: 52.1234, lon: -0.5674, elevation: 0, orientation: 90, scale: 1 },
                { name: "Oak Tree", type: "tree", lat: 52.1236, lon: -0.5676, elevation: 0, orientation: 0, scale: 1.2 },
                { name: "Old Oak", type: "tree", lat: 52.1233, lon: -0.5680, elevation: 0, orientation: 0, scale: 1.5 },
                { name: "Windmill", type: "windmill", lat: 52.1238, lon: -0.5672, elevation: 0, orientation: 45, scale: 1 },
                { name: "Shed", type: "shed", lat: 52.1232, lon: -0.5677, elevation: 0, orientation: 180, scale: 0.8 },
                { name: "Duck Pond", type: "pond", lat: 52.1235, lon: -0.5682, elevation: -0.5, orientation: 0, scale: 1 },
            ];
            
            syncScene(mockSceneData);
            document.getElementById('status').textContent = 
                `Demo mode • ${mockSceneData.length} objects • ${new Date().toLocaleTimeString()}`;
        };
        
        window.clearScene = function() {
            mockSceneData = [];
            originLat = null;
            originLon = null;
            syncScene([]);
            document.getElementById('status').textContent = 'Scene cleared';
        };
        
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        
        // Handle resize
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
        
        // Start
        animate();
        console.log('Scene viewer initialized in demo mode');
    </script>
</body>
</html>
```

Save that as `viewer.html` and open it in your browser. Click "Add Objects" to see a sample farm scene appear. The `mockSceneData` array shows exactly the format that `get_scene()` returns from the MCP server.

To connect this to a real MCP server, you'd replace the mock data with actual MCP client calls. The [@anthropic-ai/mcp-client](https://www.npmjs.com/package/@anthropic-ai/mcp-client) package handles the SSE/JSON-RPC protocol—your viewer just needs to call `client.callTool('get_scene', {})` and pass the results to `syncScene()`.

With a real connection, open Claude Desktop (configured to use the same MCP server) and say something like:

> "Create a small farm. Put a farmhouse facing south, a barn 30 meters to the east, and scatter some trees around the property."

Watch the Three.js viewer. As Claude calls the MCP tools, objects pop into existence. Move things around, add more objects, delete some—the viewer stays in sync.

## What You're Actually Seeing

This pattern—MCP server as authoritative state, LLM as interpreter, web viewer as dumb renderer—is remarkably clean. Each component does exactly one thing:

- The **server** is the source of truth. It doesn't care who's calling it or why.
- **Claude** is the brain. It understands "behind the barn" and "near the pond."
- The **viewer** is just eyes. It renders whatever it's told to render.

You could swap Three.js for Babylon.js, Unity WebGL, or a 2D Leaflet map. You could replace Claude with GPT-4 or a local model. The MCP server wouldn't know the difference.

## Going Further

This is deliberately minimal. Some obvious enhancements:

**Better geometry**: Load GLTF models instead of primitives. The `type` field could map to model URLs.

**Terrain**: Use elevation data (DEM tiles) to create actual topography. The `elevation` field would place objects on the terrain surface.

**Real-time SSE**: Instead of polling, subscribe to server events. FastMCP's SSE transport supports this—you'd need to track tool call results and push scene changes.

**Labels and interaction**: Add CSS2D labels for object names. Click to select. Drag to move (and call `set_position`).

**Shadows and atmosphere**: WebGL can do beautiful lighting. Add shadows, fog, a skybox.

**WebXR**: Three.js supports VR and AR. Walk around your conversationally-built scene.

The foundation is there. The scene data is portable, the protocol is standard, and the architecture scales.

---

*The 3D Scene MCP Server is [available on GitHub](https://github.com/andycross/mcp-geo-chat). MIT licensed. Go build something.*

