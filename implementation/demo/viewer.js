(async function () {
  const params = new URLSearchParams(window.location.search);
  const demoId = params.get("demo") || "mosquito-rockcreek";
  const demo = window.CZML_DEMOS[demoId] || window.CZML_DEMOS["mosquito-rockcreek"];

  const status = document.getElementById("status");
  document.title = `${demo.title} | Smoke CZML Viewer`;
  document.getElementById("demoKicker").textContent = demo.kicker;
  document.getElementById("demoTitle").textContent = demo.title;
  document.getElementById("demoDescription").textContent = demo.description;

  if (window.location.protocol === "file:") {
    status.textContent = "Open this demo through the local HTTP server, not as a file. Use http://127.0.0.1:8000/implementation/demo/index.html";
    return;
  }

  const referenceFrame = document.getElementById("referenceFrame");
  const referenceImage = document.getElementById("referenceImage");
  const referenceCaption = document.getElementById("referenceCaption");
  if (demo.referenceImage) {
    referenceImage.src = demo.referenceImage;
    referenceImage.alt = `${demo.title} reference`;
    referenceCaption.textContent = demo.title;
    referenceFrame.hidden = false;
  }

  Cesium.Ion.defaultAccessToken = window.CESIUM_ION_TOKEN || "";

  const viewerOptions = {
    animation: true,
    baseLayerPicker: false,
    fullscreenButton: true,
    geocoder: false,
    homeButton: true,
    infoBox: true,
    sceneModePicker: true,
    selectionIndicator: true,
    shouldAnimate: true,
    timeline: true,
    navigationHelpButton: false,
    baseLayer: Cesium.ImageryLayer.fromProviderAsync(
      Cesium.TileMapServiceImageryProvider.fromUrl(
        Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
      )
    )
  };

  async function configureTerrain(options) {
    if (!window.CESIUM_ENABLE_TERRAIN) {
      return "Terrain disabled.";
    }

    if (!window.CESIUM_ION_TOKEN) {
      return "Terrain disabled: missing Cesium Ion token.";
    }

    try {
      if (Cesium.CesiumTerrainProvider && Cesium.CesiumTerrainProvider.fromIonAssetId) {
        options.terrainProvider = await Cesium.CesiumTerrainProvider.fromIonAssetId(1, {
          requestVertexNormals: true,
          requestWaterMask: true
        });
        return "Terrain loaded from Cesium Ion asset 1.";
      }
    } catch (error) {
      console.warn("CesiumTerrainProvider.fromIonAssetId failed.", error);
    }

    try {
      if (Cesium.createWorldTerrainAsync) {
        options.terrainProvider = await Cesium.createWorldTerrainAsync({
          requestVertexNormals: true,
          requestWaterMask: true
        });
        return "Terrain loaded with createWorldTerrainAsync.";
      }
    } catch (error) {
      console.warn("createWorldTerrainAsync failed.", error);
    }

    try {
      if (Cesium.createWorldTerrain) {
        options.terrainProvider = Cesium.createWorldTerrain({
          requestVertexNormals: true,
          requestWaterMask: true
        });
        return "Terrain loaded with createWorldTerrain.";
      }
    } catch (error) {
      console.warn("createWorldTerrain failed.", error);
    }

    return "Terrain failed to initialize. Check the Cesium Ion token and allowed referrers.";
  }

  status.textContent = "Starting terrain...";
  const terrainStatus = await configureTerrain(viewerOptions);
  const viewer = new Cesium.Viewer("cesiumContainer", viewerOptions);
  console.info(terrainStatus);

  if (viewer.terrainProvider && viewer.terrainProvider.errorEvent) {
    viewer.terrainProvider.errorEvent.addEventListener((error) => {
      console.warn("Terrain provider error.", error);
      status.textContent = `Terrain error: ${error.message || "check Cesium Ion token/referrer"}`;
    });
  }

  window.addEventListener("error", (event) => {
    status.textContent = `Viewer error: ${event.message}`;
  });

  window.addEventListener("unhandledrejection", (event) => {
    const message = event.reason && event.reason.message ? event.reason.message : String(event.reason);
    status.textContent = `Viewer error: ${message}`;
  });

  function getPointColor(point, time) {
    if (!point || !point.color) {
      return undefined;
    }
    if (typeof point.color.getValue === "function") {
      return point.color.getValue(time);
    }
    return point.color;
  }

  function setClockFromDataSource(dataSource) {
    if (!dataSource.clock) {
      return;
    }
    viewer.clock.startTime = dataSource.clock.startTime.clone();
    viewer.clock.stopTime = dataSource.clock.stopTime.clone();
    viewer.clock.currentTime = dataSource.clock.currentTime.clone();
    viewer.timeline.zoomTo(viewer.clock.startTime, viewer.clock.stopTime);
  }

  function heightAlphaFactor(height, minHeight, maxHeight) {
    const floor = demo.elevationAlphaFloor ?? 0.25;
    const span = Math.max(1, maxHeight - minHeight);
    const normalized = Math.min(1, Math.max(0, (height - minHeight) / span));
    return Math.max(floor, 1 - normalized * (1 - floor));
  }

  function getHeightRange(samples) {
    if (!samples.length) {
      return { minHeight: 0, maxHeight: 1 };
    }
    let minHeight = Number.POSITIVE_INFINITY;
    let maxHeight = Number.NEGATIVE_INFINITY;
    samples.forEach((sample) => {
      minHeight = Math.min(minHeight, sample.cartographic.height);
      maxHeight = Math.max(maxHeight, sample.cartographic.height);
    });
    return { minHeight, maxHeight };
  }

  function styleDataSource(dataSource) {
    const time = viewer.clock.currentTime;
    const pointPixelSize = demo.pointPixelSize || 10;
    const alphaMultiplier = demo.particleAlphaMultiplier ?? 1;
    const positionedEntities = dataSource.entities.values
      .map((entity) => ({
        entity,
        position: entity.position && entity.position.getValue(time)
      }))
      .filter((item) => Cesium.defined(item.position));
    const heightSamples = positionedEntities.map((item) => ({
      cartographic: Cesium.Ellipsoid.WGS84.cartesianToCartographic(item.position)
    }));
    const { minHeight, maxHeight } = getHeightRange(heightSamples);

    positionedEntities.forEach(({ entity, position }) => {
      if (!entity.point) {
        return;
      }

      const color = getPointColor(entity.point, time);
      const height = Cesium.Ellipsoid.WGS84.cartesianToCartographic(position).height;
      const alpha = Math.min(1, (color ? color.alpha : 0.7) * alphaMultiplier * heightAlphaFactor(height, minHeight, maxHeight));
      const styledColor = color
        ? new Cesium.Color(color.red, color.green, color.blue, alpha)
        : Cesium.Color.WHITE.withAlpha(alpha);
      entity.point.pixelSize = new Cesium.ConstantProperty(pointPixelSize);
      entity.point.color = new Cesium.ConstantProperty(styledColor);
      entity.point.outlineWidth = new Cesium.ConstantProperty(0);
      entity.point.outlineColor = new Cesium.ConstantProperty(Cesium.Color.TRANSPARENT);
      entity.point.disableDepthTestDistance = new Cesium.ConstantProperty(Number.POSITIVE_INFINITY);
      entity.point.scaleByDistance = undefined;
      entity.point.translucencyByDistance = undefined;
    });
  }

  function getParticleSamplesAtCurrentTime(dataSources) {
    const time = viewer.clock.currentTime;
    const samples = [];

    dataSources.forEach((dataSource) => {
      dataSource.entities.values.forEach((entity) => {
        if (!entity.position) {
          return;
        }
        const position = entity.position.getValue(time);
        if (Cesium.defined(position)) {
          const color = getPointColor(entity.point, time);
          samples.push({
            position,
            color: color || Cesium.Color.WHITE.withAlpha(0.7)
          });
        }
      });
    });

    return samples;
  }

  function getParticleSamplesAcrossTimeline(dataSources) {
    const start = Cesium.JulianDate.toDate(viewer.clock.startTime).getTime();
    const stop = Cesium.JulianDate.toDate(viewer.clock.stopTime).getTime();
    const sampleCount = demo.fillerTimeSamples || 18;
    const samples = [];

    for (let i = 0; i < sampleCount; i += 1) {
      const amount = sampleCount === 1 ? 0 : i / (sampleCount - 1);
      const time = Cesium.JulianDate.fromDate(new Date(start + (stop - start) * amount));

      dataSources.forEach((dataSource) => {
        dataSource.entities.values.forEach((entity) => {
          if (!entity.position) {
            return;
          }
          const position = entity.position.getValue(time);
          if (Cesium.defined(position)) {
            const color = getPointColor(entity.point, time);
            samples.push({
              position,
              color: color || Cesium.Color.WHITE.withAlpha(0.7)
            });
          }
        });
      });
    }

    return samples;
  }

  function seededRandom(seed) {
    let value = seed % 2147483647;
    if (value <= 0) {
      value += 2147483646;
    }
    return function () {
      value = value * 16807 % 2147483647;
      return (value - 1) / 2147483646;
    };
  }

  function addFillerPointCloud(samples) {
    if (!samples.length) {
      return;
    }

    const random = seededRandom(demo.title.length * 997);
    const filler = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
    const perParticle = demo.fillerPointsPerParticle || 12;
    const maxFillerPoints = demo.maxFillerPoints || 30000;
    const pointPixelSize = demo.pointPixelSize || 10;
    const ellipsoid = Cesium.Ellipsoid.WGS84;
    const spreadMeters = demo.fillerSpreadMeters || 420;
    const nearestDistanceBias = demo.fillerNearestDistanceBias || spreadMeters * 2;
    const brownianMetersPerSecond = demo.fillerBrownianMetersPerSecond || 10;
    const maxBrownianOffsetMeters = demo.fillerBrownianMaxOffsetMeters || 50;
    const brownianPoints = [];
    const cartographicSamples = samples.map((sample) => ({
      cartographic: ellipsoid.cartesianToCartographic(sample.position),
      color: sample.color
    }));
    const { minHeight, maxHeight } = getHeightRange(cartographicSamples);
    const targetCount = Math.min(maxFillerPoints, samples.length * perParticle);
    const referenceStride = Math.max(1, Math.ceil(cartographicSamples.length / 900));
    const referenceSamples = cartographicSamples.filter((sample, index) => index % referenceStride === 0);

    function approximateDistanceMeters(a, b) {
      const lat = (a.latitude + b.latitude) * 0.5;
      const x = (a.longitude - b.longitude) * Math.cos(lat) * 6378137;
      const y = (a.latitude - b.latitude) * 6378137;
      const z = a.height - b.height;
      return Math.sqrt(x * x + y * y + z * z);
    }

    function nearestDistanceMeters(candidate) {
      let nearest = Number.POSITIVE_INFINITY;
      referenceSamples.forEach((sample) => {
        nearest = Math.min(nearest, approximateDistanceMeters(candidate, sample.cartographic));
      });
      return nearest;
    }

    for (let i = 0, attempts = 0; i < targetCount && attempts < targetCount * 14; attempts += 1) {
      const a = cartographicSamples[Math.floor(random() * cartographicSamples.length)];
      const b = cartographicSamples[Math.floor(random() * cartographicSamples.length)];
      const t = random();
      const longitude = a.cartographic.longitude * (1 - t) + b.cartographic.longitude * t;
      const latitude = a.cartographic.latitude * (1 - t) + b.cartographic.latitude * t;
      const height = a.cartographic.height * (1 - t) + b.cartographic.height * t;
      const cosLat = Math.max(0.2, Math.cos(latitude));
      const angle = random() * Math.PI * 2;
      const radius = random() * spreadMeters;
      const baseLongitude = longitude + Math.cos(angle) * radius / (6378137 * cosLat);
      const baseLatitude = latitude + Math.sin(angle) * radius / 6378137;
      const baseHeight = Math.max(0, height + (random() - 0.45) * spreadMeters * 0.45);
      const candidate = {
        longitude: baseLongitude,
        latitude: baseLatitude,
        height: baseHeight
      };
      const nearestDistance = nearestDistanceMeters(candidate);
      const keepProbability = Math.min(1, Math.max(0.06, nearestDistance / nearestDistanceBias));

      if (random() > keepProbability) {
        continue;
      }

      const baseColor = a.color;
      const alpha = Math.min(1, baseColor.alpha * heightAlphaFactor(baseHeight, minHeight, maxHeight));

      const point = filler.add({
        position: Cesium.Cartesian3.fromRadians(baseLongitude, baseLatitude, baseHeight),
        color: new Cesium.Color(baseColor.red, baseColor.green, baseColor.blue, alpha),
        outlineColor: Cesium.Color.TRANSPARENT,
        outlineWidth: 0,
        pixelSize: pointPixelSize,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      });

      brownianPoints.push({
        point,
        longitude: baseLongitude,
        latitude: baseLatitude,
        height: baseHeight,
        cosLat,
        eastOffset: 0,
        northOffset: 0,
        upOffset: 0,
        lastSeconds: undefined,
          random
        });

      i += 1;
    }

    viewer.scene.preRender.addEventListener((scene, time) => {
      const seconds = Cesium.JulianDate.secondsDifference(time, viewer.clock.startTime);
      brownianPoints.forEach((item) => {
        const lastSeconds = item.lastSeconds === undefined ? seconds : item.lastSeconds;
        const dt = Math.min(0.08, Math.max(0, seconds - lastSeconds));
        const step = brownianMetersPerSecond * Math.sqrt(dt);
        item.lastSeconds = seconds;

        item.eastOffset += (item.random() * 2 - 1) * step;
        item.northOffset += (item.random() * 2 - 1) * step;
        item.upOffset += (item.random() * 2 - 1) * step * 0.45;

        item.eastOffset = Math.max(-maxBrownianOffsetMeters, Math.min(maxBrownianOffsetMeters, item.eastOffset));
        item.northOffset = Math.max(-maxBrownianOffsetMeters, Math.min(maxBrownianOffsetMeters, item.northOffset));
        item.upOffset = Math.max(-maxBrownianOffsetMeters * 0.45, Math.min(maxBrownianOffsetMeters * 0.45, item.upOffset));

        item.point.position = Cesium.Cartesian3.fromRadians(
          item.longitude + item.eastOffset / (6378137 * item.cosLat),
          item.latitude + item.northOffset / 6378137,
          Math.max(0, item.height + item.upOffset)
        );
      });
    });
  }

  async function frameLoadedCzml(dataSources) {
    const samples = getParticleSamplesAtCurrentTime(dataSources);
    if (!samples.length) {
      await viewer.zoomTo(dataSources);
      return;
    }

    const timelineSamples = getParticleSamplesAcrossTimeline(dataSources);
    const fillerSamples = timelineSamples.length ? timelineSamples : samples;
    const positions = samples.map((sample) => sample.position);
    const sphere = Cesium.BoundingSphere.fromPoints(positions);
    const range = Math.max(demo.cameraRange || 4200, sphere.radius * 0.42);
    const headingParam = params.get("heading");
    const headingDegrees = headingParam === null ? (demo.cameraHeadingDegrees ?? 28) : Number(headingParam);
    const pitchDegrees = demo.cameraPitchDegrees ?? -4;
    addFillerPointCloud(fillerSamples);

    viewer.camera.flyToBoundingSphere(sphere, {
      duration: 1.2,
      offset: new Cesium.HeadingPitchRange(
        Cesium.Math.toRadians(((headingDegrees % 360) + 360) % 360),
        Cesium.Math.toRadians(pitchDegrees),
        range
      )
    });
  }

  try {
    status.textContent = "Loading smoke CZML...";
    const smoke = await Cesium.CzmlDataSource.load(demo.smoke);
    viewer.dataSources.add(smoke);
    setClockFromDataSource(smoke);
    styleDataSource(smoke);

    const dataSources = [smoke];

    status.textContent = "Loading cloud CZML...";
    try {
      const clouds = await Cesium.CzmlDataSource.load(demo.clouds);
      viewer.dataSources.add(clouds);
      styleDataSource(clouds);
      if (clouds.entities.values.length > 0) {
        dataSources.push(clouds);
      }
    } catch (cloudError) {
      console.warn("Cloud CZML did not load; continuing with smoke only.", cloudError);
    }

    status.textContent = "Framing smoke particles...";
    await frameLoadedCzml(dataSources);

    status.textContent = dataSources.length > 1 ? "Loaded smoke and cloud CZML." : "Loaded smoke CZML.";
  } catch (error) {
    console.error(error);
    status.textContent = `Unable to load smoke CZML: ${error.message || error}`;
  }
})();
