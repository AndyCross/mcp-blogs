+++
title = "Building 3D Scenes Through Conversation: An MCP Server for Geographic Objects"
date = "2024-12-02"
draft = false
tags = ["mcp", "ai", "python", "gis"]
+++

I've been noodling around with the Model Context Protocol lately, and I wanted to share something I've built that demonstrates what I think is a rather interesting pattern: how you can split responsibilities between an AI and a server in a way that plays to each of their strengths.

The project is a 3D scene builder. But before you start thinking about meshes, textures, and rendering pipelines, stop. This isn't that. It's far more minimal, and I'd argue, far more useful as a foundation.

## What It Actually Does

The server maintains a collection of named objects in real-world geographic space. That's it. No rendering, no assets, no visual output. Just a spatial registry that speaks in WGS84 coordinates, the same system your phone's GPS uses.

Every object has:

| Property | What it is |
|----------|-----------|
| `name` | Unique identifier ("Home", "Garden Oak", "The Shed") |
| `type` | Freeform descriptor. Could be "house", "ancient oak", or "portal to dimension X" |
| `lat/lon` | Decimal degrees, WGS84 |
| `elevation` | Metres above sea level |
| `orientation` | Degrees clockwise from north |
| `scale` | Uniform scale factor |

Why so minimal? Because downstream systems can interpret this data however they like. Feed it to a game engine, a GIS tool, a mapping API, whatever. The scene server doesn't care about rendering. It cares about *where things are*.

## The Interesting Bit: Who Does What

Here's where it gets good. The server is deliberately precise and dumb. It speaks in absolute coordinates only. If you want to place something "20 metres southwest", the server has no idea what that means. It just knows lat/lon.

Claude, on the other hand, is brilliant at understanding spatial language. "Behind the house", "near the oak tree", "along the path". This is exactly the kind of fuzzy human concept that LLMs handle well.

So the division of labour is:

- **Server**: Storage, geodesic maths, geocoding
- **Claude**: Natural language interpretation, spatial reasoning, orchestration

Let me show you what this looks like in practice.

## Real Conversation Patterns

### "Add a house on the corner of Kiln Close and Church Lane"

Claude's thinking here:

1. User wants an object at a real-world location
2. Need to convert that address to coordinates → call `geocode`
3. `geocode("corner of Kiln Close and Church Lane")` returns coords plus a confidence level
4. If confidence is low (say, "city" level), ask for clarification
5. If confident, call `add_object(name="Home", type="house", lat=52.1234, lon=-0.5678)`

The server provides the geocoding (via OpenStreetMap Nominatim) and the storage. Claude handles the conversational flow and error handling.

### "Move Home 20 metres southwest"

This is where the split really shines:

1. Claude interprets "20 metres southwest" → bearing of 225°, distance of 20m
2. `get_object("Home")` → fetches current position
3. `calculate_offset(lat=52.1234, lon=-0.5678, bearing=225, distance=20)` → server does the geodesic maths
4. `set_position("Home", lat=52.1232, lon=-0.5680)` → new position set

The server handles the tricky bit: calculating what "20 metres at bearing 225" means on a sphere. Claude just needs to know that southwest = 225°.

### "Put a shed behind the house"

This one's fun because "behind" is entirely contextual:

1. `get_object("Home")` → gets position and crucially, *orientation* (say, 180° = facing south)
2. Claude reasons: "behind" = opposite of facing direction = 0° (north)
3. Picks a reasonable distance (5m? 10m?) based on context
4. `calculate_offset(...)` with the computed bearing
5. `add_object(name="Shed", type="shed", ...)`

The server has no concept of "behind". It just knows coordinates and orientations. Claude does the spatial reasoning.

## The Toolset

The server exposes a focused set of tools:

**Creating/Destroying:**
- `add_object`: place something in the scene
- `remove_object`: delete by name

**Transforming:**
- `set_position`: move to new coordinates
- `set_orientation`: rotate
- `set_scale`: resize

**Querying:**
- `get_object`: full details of one object
- `list_objects`: all objects, optionally filtered by type

**Utilities:**
- `geocode`: natural language → coordinates
- `calculate_offset`: "from here, go X metres at bearing Y"

**Scene management:**
- `get_scene`: export everything
- `set_scene`: import/replace everything

That's the entire API. Twelve tools. No more than needed.

## Why This Pattern Matters

I think there's a broader lesson here about building MCP servers. The temptation is to make them smart, to handle natural language, fuzzy inputs, contextual interpretation. But that's Claude's job. That's what the LLM is *for*.

Your MCP server should be:

1. **Precise**: clear inputs, predictable outputs
2. **Minimal**: do one thing well
3. **Portable**: standard formats (WGS84, JSON, etc.)
4. **Stateless where possible**: let the client handle persistence

The magic happens at the boundary. Claude interprets "the old oak tree by the pond" and turns it into a geocode query. The server returns precise coordinates. Claude stores the object. Later, when you say "move it closer to the house", Claude knows which object you mean, calculates what "closer" means in spatial terms, and calls the appropriate tools.

Neither system is doing something it's bad at. That's the whole point.

## Running It Yourself

If you want to have a play:

```bash
pip install fastmcp pyproj geopy
```

Clone the repo, install, and run:

```bash
scene-mcp
```

By default it uses stdio transport (for Claude Desktop). For web clients:

```bash
SCENE_MCP_TRANSPORT=http SCENE_MCP_PORT=8080 scene-mcp
```

Then connect your MCP client and start describing scenes. "Create a small village with a pub, a church, and a village green." See what happens.

## What's Next

This is foundation work. The scene data is portable. It's just coordinates and metadata. You could feed it to:

- A game engine (Unreal, Unity, Godot)
- A GIS visualisation tool
- A procedural terrain generator
- A VR environment builder
- Literally anything that understands lat/lon

The point is to separate *scene description* from *scene rendering*. Let conversations build the spatial model. Let specialised tools handle the visuals.

That's the bet, anyway. I'll write more as I build out the rendering side. For now, give the scene server a go and let me know what you think.

---

*The 3D Scene MCP Server is [available on GitHub](https://github.com/andycross/mcp-geo-chat). It's MIT licensed because life's too short for anything else.*

