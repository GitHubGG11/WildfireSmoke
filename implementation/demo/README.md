# Smoke CZML Demo

This folder is a static Cesium demo for viewing saved smoke/cloud CZML outputs.

It is designed to work locally and on GitHub Pages. The demo CZML files and reference images live under `czmlDemoFiles`, so the viewer does not need to reach back into the original research-output folders.

## Local Usage

From the project root, start a static server:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8000/implementation/demo/index.html
```

Do not open `index.html` directly with `file://`; Cesium needs HTTP fetches to load CZML files reliably.

## Files

- `index.html` - landing page with camera/demo choices
- `viewer.html` - Cesium viewer page
- `demos.js` - demo definitions and tuning parameters
- `viewer.js` - CZML loading, terrain, camera framing, particle fill logic
- `styles.css` - page styling
- `czmlDemoFiles/` - copied CZML files and reference images used by the demo

## GitHub Pages

After pushing this repo to GitHub:

1. Go to the repo on GitHub.
2. Open `Settings`.
3. Open `Pages`.
4. Under `Build and deployment`, choose `Deploy from a branch`.
5. Select the branch, usually `main`.
6. Select `/root` as the folder.
7. Save.

Your demo URL should look like:

```text
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/implementation/demo/index.html
```

The demo uses local relative paths such as:

```js
"czmlDemoFiles/CZMLs/mosquito-rockcreek/smoke.czml"
```

So the `implementation/demo/czmlDemoFiles` folder must be pushed with the repo.

## Add A New Demo

Add an entry in `demos.js`:

```js
"my-demo-id": {
  title: "Fire Name: Camera Name",
  kicker: "Fire name",
  description: "Short description.",
  referenceImage: "czmlDemoFiles/czmlImages/my-demo-id/reference.jpg",
  smoke: "czmlDemoFiles/CZMLs/my-demo-id/smoke.czml",
  clouds: "czmlDemoFiles/CZMLs/my-demo-id/clouds.czml",
  cameraRange: 5600,
  cameraHeadingDegrees: 28,
  cameraPitchDegrees: -4,
  pointPixelSize: 10,
  particleAlphaMultiplier: 0.42,
  elevationAlphaFloor: 0.22,
  fillerPointsPerParticle: 55,
  maxFillerPoints: 42000,
  fillerTimeSamples: 32,
  fillerSpreadMeters: 360,
  fillerNearestDistanceBias: 720,
  fillerBrownianMetersPerSecond: 11,
  fillerBrownianMaxOffsetMeters: 55
}
```

Then add a card in `index.html`:

```html
<a class="demo-card" href="viewer.html?demo=my-demo-id">
  <span class="demo-kicker">Fire Name</span>
  <strong>Camera Name</strong>
  <span>Short description.</span>
</a>
```

## Tuning

All main visual controls are in `demos.js`.

- `cameraRange`: larger means the camera starts farther away
- `cameraHeadingDegrees`: 0-360 degree orbit angle around the smoke for the initial view
- `cameraPitchDegrees`: vertical camera angle; closer to 0 is more level, more negative looks downward
- `pointPixelSize`: particle size
- `particleAlphaMultiplier`: opacity multiplier for real and added particles
- `elevationAlphaFloor`: minimum opacity for high-elevation particles
- `fillerPointsPerParticle`: density of added particles
- `maxFillerPoints`: total cap for added particles
- `fillerTimeSamples`: how many CZML times are sampled for added particles
- `fillerSpreadMeters`: spatial spread around generated particles
- `fillerNearestDistanceBias`: controls gap-filling based on distance from nearest CZML point
- `fillerBrownianMetersPerSecond`: random-walk motion strength
- `fillerBrownianMaxOffsetMeters`: max random-walk distance from each generated point

You can also test a different heading directly in the URL:

```text
viewer.html?demo=mosquito-rockcreek&heading=180
```

## Terrain

Terrain is enabled in `demos.js`:

```js
window.CESIUM_ENABLE_TERRAIN = true;
window.CESIUM_ION_TOKEN = "...";
```

Cesium World Terrain requires an Ion token. If terrain does not load on GitHub Pages, check that the token allows your GitHub Pages domain.

## Generate New Physics CZML

The implementation also includes a compact physics generator:

```powershell
python -m implementation.physics.generate
```

It writes:

```text
implementation/output/physics_smoke.czml
implementation/output/physics_clouds.czml
```

You can add those outputs to `demos.js` the same way as the existing smoke/cloud files.
