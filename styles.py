"""styles.py - Editorial CSS, bike loader, autofill & Leaflet map overlay."""

GOOGLE_FONTS_HEADER = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;'
    '500;600;700&family=JetBrains+Mono:wght@500;600;700'
    '&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">'
)

# Browser enhancement script registered via Drafter add_website_js() and
# activated in Pyodide via install_browser_map_enhancer():
# 1. Guards Leaflet invalidateSize() against Drafter v2.3.2's unmount race.
# 2. Replaces generic blue circleMarkers with labeled green A & red B pins.
# 3. Draws color-coded street-following Leaflet polylines from data_polylines.
# 4. Powers the animated bicycle loading overlay during boot & route queries.
# 5. Powers fast local + live OpenStreetMap Photon location autofill dropdowns.
DRAFTER_MAP_GUARD_JS = """
(function () {
  if (window.__scMapEnhancerInstalled) return;
  window.__scMapEnhancerInstalled = true;

  var SHADOW_PIN_CSS =
    ".sc-map-pin-wrap{background:transparent!important;border:none!important;}" +
    ".sc-map-pin{width:28px;height:28px;border-radius:50%;display:flex;" +
    "align-items:center;justify-content:center;font-family:system-ui,sans-serif;" +
    "font-size:13px;font-weight:800;color:#ffffff;border:2.5px solid #ffffff;" +
    "box-shadow:0 2px 6px rgba(15,23,42,0.4);}" +
    ".sc-map-pin-start{background:#047857;}" +
    ".sc-map-pin-dest{background:#dc2626;}" +
    ".sc-map-pin-point{width:18px;height:18px;margin:5px;font-size:10px;" +
    "background:#0f172a;}" +
    ".sc-map-badge-wrap{background:transparent!important;border:none!important;}" +
    ".sc-map-badge{display:inline-flex;align-items:center;gap:4px;" +
    "padding:2px 6px;border-radius:6px;font-family:system-ui,sans-serif;" +
    "font-size:10.5px;font-weight:700;line-height:1.15;white-space:nowrap;" +
    "cursor:pointer;background:rgba(255,255,255,0.96);color:#0f172a;" +
    "border:1.5px solid #64748b;box-shadow:0 2px 6px rgba(15,23,42,0.24);" +
    "transform:translate(-50%,-50%);transition:transform 140ms ease," +
    "padding 140ms ease,box-shadow 140ms ease,border-color 140ms ease;}" +
    ".sc-map-badge .sc-badge-full{display:none;}" +
    ".sc-map-badge:hover,.sc-map-badge.sc-badge-hovered," +
    ".sc-map-badge.sc-map-badge-active{padding:3px 8px;font-size:11px;gap:5px;}" +
    ".sc-map-badge:hover .sc-badge-short," +
    ".sc-map-badge.sc-badge-hovered .sc-badge-short," +
    ".sc-map-badge.sc-map-badge-active .sc-badge-short{display:none;}" +
    ".sc-map-badge:hover .sc-badge-full," +
    ".sc-map-badge.sc-badge-hovered .sc-badge-full," +
    ".sc-map-badge.sc-map-badge-active .sc-badge-full{display:inline;}" +
    ".sc-map-badge:hover,.sc-map-badge.sc-badge-hovered{" +
    "transform:translate(-50%,-54%) scale(1.04);border-color:#047857;" +
    "box-shadow:0 4px 12px rgba(15,23,42,0.32);}" +
    ".sc-map-badge.sc-map-badge-active{background:#047857;color:#ffffff;" +
    "border-color:#ffffff;box-shadow:0 4px 12px rgba(4,120,87,0.42);}" +
    ".sc-map-badge-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;" +
    "border:1px solid rgba(255,255,255,0.9);}" +
    ".leaflet-interactive{cursor:pointer!important;}";

  var WHEEL_SVG =
    '<svg viewBox="0 0 38 38" width="38" height="38" fill="none">' +
    '<circle cx="19" cy="19" r="16.5" stroke="currentColor" stroke-width="3.2"/>' +
    '<circle cx="19" cy="19" r="2.5" fill="currentColor"/>' +
    '<line x1="19" y1="3" x2="19" y2="35" stroke="currentColor" ' +
    'stroke-opacity="0.45" stroke-width="1.5"/>' +
    '<line x1="3" y1="19" x2="35" y2="19" stroke="currentColor" ' +
    'stroke-opacity="0.45" stroke-width="1.5"/>' +
    '<line x1="7.7" y1="7.7" x2="30.3" y2="30.3" stroke="currentColor" ' +
    'stroke-opacity="0.45" stroke-width="1.5"/>' +
    '<line x1="30.3" y1="7.7" x2="7.7" y2="30.3" stroke="currentColor" ' +
    'stroke-opacity="0.45" stroke-width="1.5"/></svg>';

  var FRAME_SVG =
    '<svg viewBox="0 0 140 82" width="140" height="82" fill="none">' +
    '<path d="M34 54 L60 54 L88 28 L53 28 Z" stroke="var(--sc-brand)" ' +
    'stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/>' +
    '<path d="M60 54 L49 22 M43 22 L56 22" stroke="currentColor" ' +
    'stroke-width="3.2" stroke-linecap="round"/>' +
    '<path d="M104 54 L87 22 L99 20 C103 20 105 24 102 27" ' +
    'stroke="currentColor" stroke-width="3.2" stroke-linecap="round" ' +
    'stroke-linejoin="round"/>' +
    '<circle cx="60" cy="54" r="3.5" fill="var(--sc-brand)"/></svg>';

  var BIKE_LOADER_HTML =
    '<div class="sc-bike-stage" aria-hidden="true">' +
    '<div class="sc-road-clip"><div class="sc-road-track"></div></div>' +
    '<div class="sc-bike-body">' +
    '<div class="sc-wheel-layer sc-wheel-rear">' +
    WHEEL_SVG +
    '</div><div class="sc-wheel-layer sc-wheel-front">' +
    WHEEL_SVG +
    '</div><div class="sc-frame-layer">' +
    FRAME_SVG +
    "</div></div></div>";

  var photonCache = new Map();
  var activeHideTimer = null;

  function isDarkActive() {
    return Boolean(document.querySelector(".sc-app-shell.sc-dark"));
  }

  function syncBodyTheme() {
    var dark = isDarkActive();
    document.documentElement.classList.toggle("sc-dark-root", dark);
    if (document.body) {
      document.body.classList.toggle("sc-dark-root", dark);
    }
    var loader = document.getElementById("sc-bike-loader");
    if (loader) {
      loader.classList.toggle("sc-dark", dark);
    }
  }

  function ensureBikeLoader() {
    var existing = document.getElementById("sc-bike-loader");
    if (existing) return existing;
    var overlay = document.createElement("div");
    overlay.id = "sc-bike-loader";
    overlay.className =
      "sc-bike-loader sc-loader-hidden" + (isDarkActive() ? " sc-dark" : "");
    overlay.setAttribute("role", "status");
    overlay.setAttribute("aria-live", "polite");
    overlay.innerHTML =
      '<div class="sc-bike-loader-card">' +
      BIKE_LOADER_HTML +
      '<div class="sc-bike-loader-title">SafeCycle</div>' +
      '<div class="sc-bike-loader-sub" id="sc-bike-loader-msg">' +
      "Mapping safer bike streets...</div></div>";
    document.body.appendChild(overlay);
    return overlay;
  }

  function showBikeLoader(message) {
    if (activeHideTimer) {
      clearTimeout(activeHideTimer);
      activeHideTimer = null;
    }
    var loader = ensureBikeLoader();
    loader.classList.toggle("sc-dark", isDarkActive());
    var msgEl = document.getElementById("sc-bike-loader-msg");
    if (msgEl && message) {
      msgEl.textContent = message;
    }
    loader.classList.remove("sc-loader-hidden");
    loader.classList.add("sc-loader-visible");
    void loader.offsetWidth;
  }

  function hideBikeLoader(delayMs) {
    var loader = document.getElementById("sc-bike-loader");
    if (!loader) return;
    if (activeHideTimer) {
      clearTimeout(activeHideTimer);
    }
    activeHideTimer = setTimeout(function () {
      loader.classList.remove("sc-loader-visible");
      loader.classList.add("sc-loader-hidden");
      activeHideTimer = null;
    }, delayMs || 120);
  }

  window.__scShowBikeLoader = showBikeLoader;
  window.__scHideBikeLoader = hideBikeLoader;

  function ensureShadowStyles(el) {
    if (!el || !el.shadowRoot) return;
    if (el.shadowRoot.querySelector("style[data-sc-pin-css]")) return;
    var styleEl = document.createElement("style");
    styleEl.setAttribute("data-sc-pin-css", "1");
    styleEl.textContent = SHADOW_PIN_CSS;
    el.shadowRoot.appendChild(styleEl);
  }

  function isMapDetached(mapObj) {
    return (
      !mapObj ||
      !mapObj._loaded ||
      !mapObj._mapPane ||
      !mapObj._mapPane._leaflet_pos ||
      !mapObj._container ||
      !mapObj._container.isConnected
    );
  }

  function guardLeafletMap(mapInst) {
    if (!mapInst) return;
    var proto = Object.getPrototypeOf(mapInst);
    if (!proto || proto.__scSafeInvalidate) return;
    var guarded = ["invalidateSize", "_onZoomTransitionEnd", "_move"];
    for (var i = 0; i < guarded.length; i += 1) {
      (function (fnName) {
        if (typeof proto[fnName] !== "function") return;
        var origFn = proto[fnName];
        proto[fnName] = function () {
          if (isMapDetached(this)) return this;
          try {
            return origFn.apply(this, arguments);
          } catch (err) {
            if (err && String(err.message || err).indexOf("_leaflet_pos") !== -1) {
              return this;
            }
            throw err;
          }
        };
      })(guarded[i]);
    }
    proto.__scSafeInvalidate = true;
  }

  function makePinIcon(L, labelText) {
    var lower = String(labelText || "").toLowerCase();
    var cls = "sc-map-pin sc-map-pin-point";
    var badge = "•";
    if (lower.indexOf("start") === 0) {
      cls = "sc-map-pin sc-map-pin-start";
      badge = "S";
    } else if (
      lower.indexOf("destination") === 0 ||
      lower.indexOf("end") === 0
    ) {
      cls = "sc-map-pin sc-map-pin-dest";
      badge = "E";
    }
    return L.divIcon({
      className: "sc-map-pin-wrap",
      html: '<div class="' + cls + '">' + badge + "</div>",
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
  }

  function renderCleanMarkers(el) {
    var L = window.L;
    if (!el || !el.map || !el.markerLayer || !L) return;
    ensureShadowStyles(el);
    el.markerLayer.clearLayers();
    var raw = el.getAttribute("markers");
    if (!raw) return;
    var items = [];
    try {
      items = JSON.parse(raw);
    } catch (err) {
      return;
    }
    for (var i = 0; i < items.length; i += 1) {
      var item = items[i];
      if (!item) continue;
      var lat = Number(item.latitude);
      var lon = Number(item.longitude);
      if (isNaN(lat) || isNaN(lon)) continue;
      var label = item.label || "";
      var marker = L.marker([lat, lon], {
        icon: makePinIcon(L, label),
        zIndexOffset: 900,
      });
      if (label) {
        marker.bindTooltip(label, { direction: "top", offset: [0, -14] });
      }
      marker.addTo(el.markerLayer);
    }
  }

  function selectRouteFromMap(routeMode) {
    if (!routeMode) return;
    var btn = document.querySelector(
      'button[data_route_mode="' +
        routeMode +
        '"], button[data-route-mode="' +
        routeMode +
        '"]'
    );
    if (!btn) {
      var tabs = document.querySelectorAll("button.sc-route-tab");
      for (var i = 0; i < tabs.length; i += 1) {
        var txt = (tabs[i].textContent || "").trim();
        if (txt.indexOf(routeMode) === 0) {
          btn = tabs[i];
          break;
        }
      }
    }
    if (btn && !btn.classList.contains("sc-route-tab-active")) {
      btn.click();
    }
  }

  function setBadgeHoverState(el, modeName, isHover) {
    if (!el || !el.shadowRoot || !modeName) return;
    var node = el.shadowRoot.querySelector(
      '[data-route-badge="' + modeName + '"]'
    );
    if (node) {
      node.classList.toggle("sc-badge-hovered", Boolean(isHover));
    }
  }

  function renderRoutePolylines(el) {
    var L = window.L;
    if (!el || !el.map || !L) return;
    ensureShadowStyles(el);
    if (el.__scRouteLayer) {
      try {
        el.__scRouteLayer.clearLayers();
      } catch (err) {
        el.__scRouteLayer = null;
      }
    } else {
      el.__scRouteLayer = L.layerGroup().addTo(el.map);
    }
    var raw =
      el.getAttribute("data_polylines") || el.getAttribute("data-polylines");
    var boundsPts = [];
    var badgeMarkers = [];
    var polyByMode = {};
    if (raw) {
      try {
        var items = JSON.parse(raw);
        for (var i = 0; i < items.length; i += 1) {
          var item = items[i];
          if (!item) continue;
          if (item.kind === "badge") {
            var bLat = Number(item.lat);
            var bLon = Number(item.lon);
            if (isNaN(bLat) || isNaN(bLon)) continue;
            var badgeCls = item.active
              ? "sc-map-badge sc-map-badge-active"
              : "sc-map-badge";
            var dotColor = item.color || "#047857";
            var shortTxt = String(item.shortText || item.text || "");
            var fullTxt = String(item.fullText || item.text || "");
            var badgeHtml =
              '<div class="' +
              badgeCls +
              '" data-route-badge="' +
              String(item.routeMode || "") +
              '"><span class="sc-map-badge-dot" style="background:' +
              dotColor +
              '"></span><span class="sc-badge-short">' +
              shortTxt +
              '</span><span class="sc-badge-full">' +
              fullTxt +
              "</span></div>";
            var badgeMarker = L.marker([bLat, bLon], {
              icon: L.divIcon({
                className: "sc-map-badge-wrap",
                html: badgeHtml,
                iconSize: [0, 0],
                iconAnchor: [0, 0],
              }),
              zIndexOffset: item.active ? 700 : 450,
            });
            (function (modeName, isActBadge) {
              badgeMarker.on("mouseover", function () {
                var p = polyByMode[modeName];
                if (p && !isActBadge) {
                  p.setStyle({ color: "#0284c7", weight: 6, opacity: 0.94 });
                }
              });
              badgeMarker.on("mouseout", function () {
                var p = polyByMode[modeName];
                if (p && !isActBadge) {
                  p.setStyle({ color: "#64748b", weight: 4.5, opacity: 0.72 });
                }
              });
              badgeMarker.on("click", function (ev) {
                if (L.DomEvent) L.DomEvent.stopPropagation(ev);
                selectRouteFromMap(modeName);
              });
            })(item.routeMode, Boolean(item.active));
            badgeMarker.addTo(el.__scRouteLayer);
            badgeMarkers.push(badgeMarker);
            continue;
          }
          if (!item.coords || item.coords.length < 2) continue;
          var isAct = item.isActive !== false;
          L.polyline(item.coords, {
            color: "#ffffff",
            weight: (item.weight || 5) + 3,
            opacity: isAct ? 0.92 : 0.72,
            lineCap: "round",
            lineJoin: "round",
            interactive: false,
          }).addTo(el.__scRouteLayer);
          var baseColor = item.color || "#047857";
          var baseWeight = item.weight || 5;
          var baseOpacity = item.opacity != null ? item.opacity : 0.9;
          var poly = L.polyline(item.coords, {
            color: baseColor,
            weight: baseWeight,
            opacity: baseOpacity,
            dashArray: item.dashArray || null,
            lineCap: "round",
            lineJoin: "round",
          });
          if (item.routeMode) {
            polyByMode[item.routeMode] = poly;
          }
          if (!isAct && item.routeMode) {
            (function (p, modeName, origColor, origWeight, origOpacity) {
              p.on("mouseover", function () {
                p.setStyle({ color: "#0284c7", weight: 6, opacity: 0.94 });
                setBadgeHoverState(el, modeName, true);
              });
              p.on("mouseout", function () {
                p.setStyle({
                  color: origColor,
                  weight: origWeight,
                  opacity: origOpacity,
                });
                setBadgeHoverState(el, modeName, false);
              });
              p.on("click", function (ev) {
                if (L.DomEvent) L.DomEvent.stopPropagation(ev);
                selectRouteFromMap(modeName);
              });
            })(poly, item.routeMode, baseColor, baseWeight, baseOpacity);
          } else if (item.label) {
            poly.bindTooltip(item.label, { sticky: true });
          }
          poly.addTo(el.__scRouteLayer);
          for (var j = 0; j < item.coords.length; j += 1) {
            boundsPts.push(item.coords[j]);
          }
        }
      } catch (err) {
        /* ignore malformed polyline JSON */
      }
    }
    var endpointLatLngs = [];
    var rawMarkers = el.getAttribute("markers");
    if (rawMarkers) {
      try {
        var pts = JSON.parse(rawMarkers);
        for (var m = 0; m < pts.length; m += 1) {
          var ep = [Number(pts[m].latitude), Number(pts[m].longitude)];
          if (!isNaN(ep[0]) && !isNaN(ep[1])) {
            endpointLatLngs.push(ep);
            boundsPts.push(ep);
          }
        }
      } catch (err) {
        /* ignore */
      }
    }
    if (boundsPts.length >= 2 && el.map._mapPane) {
      try {
        el.map.fitBounds(L.latLngBounds(boundsPts), {
          padding: [44, 44],
          maxZoom: 15,
          animate: false,
        });
      } catch (err) {
        /* ignore bounds errors */
      }
    }
    if (badgeMarkers.length > 0 && el.map._mapPane) {
      try {
        var mapSize = el.map.getSize();
        var padX = 52;
        var padY = 26;
        var epPts = [];
        for (var e = 0; e < endpointLatLngs.length; e += 1) {
          epPts.push(el.map.latLngToContainerPoint(endpointLatLngs[e]));
        }
        var placedPts = [];
        var offsets = [
          [0, 0],
          [0, -34],
          [0, 34],
          [66, 0],
          [-66, 0],
          [56, -34],
          [-56, -34],
          [56, 34],
          [-56, 34],
          [0, -64],
          [0, 64],
          [92, -26],
          [-92, -26],
          [92, 26],
          [-92, 26],
        ];
        function hasCollision(cand) {
          for (var epIdx = 0; epIdx < epPts.length; epIdx += 1) {
            if (
              Math.abs(cand.x - epPts[epIdx].x) < 88 &&
              Math.abs(cand.y - epPts[epIdx].y) < 50
            ) {
              return true;
            }
          }
          for (var pIdx = 0; pIdx < placedPts.length; pIdx += 1) {
            if (
              Math.abs(cand.x - placedPts[pIdx].x) < 92 &&
              Math.abs(cand.y - placedPts[pIdx].y) < 30
            ) {
              return true;
            }
          }
          return false;
        }
        for (var b = 0; b < badgeMarkers.length; b += 1) {
          var bm = badgeMarkers[b];
          var origPt = el.map.latLngToContainerPoint(bm.getLatLng());
          var chosen = origPt;
          for (var o = 0; o < offsets.length; o += 1) {
            var cx = Math.max(
              padX,
              Math.min(mapSize.x - padX, origPt.x + offsets[o][0])
            );
            var cy = Math.max(
              padY,
              Math.min(mapSize.y - padY, origPt.y + offsets[o][1])
            );
            var cand = L.point(cx, cy);
            if (!hasCollision(cand)) {
              chosen = cand;
              break;
            }
          }
          bm.setLatLng(el.map.containerPointToLatLng(chosen));
          placedPts.push(chosen);
        }
      } catch (err) {
        /* ignore screen projection errors */
      }
    }
  }

  function patchDrafterMapElement() {
    var cls = customElements.get("drafter-map");
    if (!cls || !cls.prototype || cls.prototype.__scLeafletPatched) return;
    cls.prototype.__scLeafletPatched = true;
    var origBuild = cls.prototype.buildMap;
    var origSync = cls.prototype.syncMarkers;
    var origDisc = cls.prototype.disconnectedCallback;

    if (typeof origSync === "function") {
      cls.prototype.syncMarkers = function () {
        if (window.L) {
          renderCleanMarkers(this);
          renderRoutePolylines(this);
        } else {
          origSync.apply(this, arguments);
        }
      };
    }

    if (typeof origBuild === "function") {
      cls.prototype.buildMap = function () {
        var res = origBuild.apply(this, arguments);
        guardLeafletMap(this && this.map);
        renderCleanMarkers(this);
        renderRoutePolylines(this);
        return res;
      };
    }

    if (typeof origDisc === "function") {
      cls.prototype.disconnectedCallback = function () {
        if (this.__scRouteLayer) {
          try {
            this.__scRouteLayer.clearLayers();
          } catch (err) {
            /* ignore */
          }
          this.__scRouteLayer = null;
        }
        return origDisc.apply(this, arguments);
      };
    }

    var existing = document.querySelectorAll("drafter-map");
    for (var i = 0; i < existing.length; i += 1) {
      guardLeafletMap(existing[i] && existing[i].map);
      renderCleanMarkers(existing[i]);
      renderRoutePolylines(existing[i]);
    }
  }

  function parseCatalog(inputEl) {
    var raw =
      inputEl.getAttribute("data_suggestions") ||
      inputEl.getAttribute("data-suggestions");
    if (!raw) return [];
    try {
      return JSON.parse(raw);
    } catch (err) {
      return [];
    }
  }

  function formatPhotonFeature(feat) {
    var props = (feat && feat.properties) || {};
    var coords = (feat && feat.geometry && feat.geometry.coordinates) || [];
    var primary =
      props.name ||
      (props.housenumber && props.street
        ? props.housenumber + " " + props.street
        : props.street) ||
      props.city ||
      "";
    var detailParts = [];
    if (props.street && props.street !== primary) detailParts.push(props.street);
    if (props.city && props.city !== primary) detailParts.push(props.city);
    if (props.state) detailParts.push(props.state);
    var detail = detailParts.join(", ");
    var full = detail ? primary + ", " + detail : primary;
    return {
      name: full,
      title: primary || full,
      meta: detail || props.country || "OpenStreetMap",
      lat: coords.length >= 2 ? Number(coords[1]) : null,
      lon: coords.length >= 2 ? Number(coords[0]) : null,
    };
  }

  function parseLatLonInput(raw) {
    var parts = String(raw || "").split(",");
    if (parts.length !== 2) return null;
    var lat = parseFloat(parts[0].trim());
    var lon = parseFloat(parts[1].trim());
    if (
      isNaN(lat) ||
      isNaN(lon) ||
      lat < -90 ||
      lat > 90 ||
      lon < -180 ||
      lon > 180
    ) {
      return null;
    }
    return { lat: lat, lon: lon };
  }

  function updatePlannerMapPin(isStart, lat, lon, label) {
    var mapEl = document.querySelector("drafter-map");
    if (!mapEl || !mapEl.map || !window.L) return;
    if (mapEl.getAttribute("data_polylines") || mapEl.getAttribute("data-polylines")) {
      return;
    }
    var items = [];
    try {
      items = JSON.parse(mapEl.getAttribute("markers") || "[]");
    } catch (err) {
      items = [];
    }
    var prefix = isStart ? "Start (S): " : "End (E): ";
    var targetIdx = isStart ? 0 : 1;
    while (items.length <= targetIdx) {
      items.push({ latitude: lat, longitude: lon, label: prefix + label });
    }
    items[targetIdx] = {
      latitude: Number(lat),
      longitude: Number(lon),
      label: prefix + String(label || ""),
    };
    mapEl.setAttribute("markers", JSON.stringify(items));
    renderCleanMarkers(mapEl);
    var bounds = [];
    for (var i = 0; i < items.length; i += 1) {
      var la = Number(items[i].latitude);
      var lo = Number(items[i].longitude);
      if (!isNaN(la) && !isNaN(lo)) bounds.push([la, lo]);
    }
    if (bounds.length >= 2 && mapEl.map._mapPane) {
      try {
        mapEl.map.fitBounds(window.L.latLngBounds(bounds), {
          padding: [48, 48],
          maxZoom: 14,
          animate: false,
        });
      } catch (err) {
        /* ignore bounds error */
      }
    }
  }

  function attachLocationAutocomplete(inputEl) {
    if (!inputEl || inputEl.__scAutofillBound) return;
    inputEl.__scAutofillBound = true;
    inputEl.setAttribute("autocomplete", "off");
    inputEl.setAttribute("aria-autocomplete", "list");

    var isStartInput = inputEl.getAttribute("name") === "start_address";
    var catalog = parseCatalog(inputEl);
    var host = inputEl.parentElement;
    if (!host) return;
    host.classList.add("sc-autofill-host");

    var listEl = document.createElement("div");
    listEl.className = "sc-autofill-menu";
    listEl.setAttribute("role", "listbox");
    listEl.style.display = "none";
    host.appendChild(listEl);

    var currentItems = [];
    var activeIdx = -1;
    var debounceId = null;
    var abortCtrl = null;
    var suppressNextInput = false;
    var menuLockedClosed = false;

    function cancelPendingFetch() {
      if (debounceId) {
        clearTimeout(debounceId);
        debounceId = null;
      }
      if (abortCtrl) {
        abortCtrl.abort();
        abortCtrl = null;
      }
    }

    function closeMenu() {
      listEl.style.display = "none";
      activeIdx = -1;
    }

    function syncPinForText(textVal) {
      var q = String(textVal || "").trim();
      if (!q) return;
      var pair = parseLatLonInput(q);
      if (pair) {
        updatePlannerMapPin(isStartInput, pair.lat, pair.lon, q);
        return;
      }
      var lower = q.toLowerCase();
      for (var i = 0; i < catalog.length; i += 1) {
        var c = catalog[i];
        var cname = String(c.name || "").toLowerCase();
        if (
          (cname === lower || cname.indexOf(lower) !== -1) &&
          c.lat != null &&
          c.lon != null
        ) {
          updatePlannerMapPin(isStartInput, c.lat, c.lon, c.name);
          return;
        }
      }
      if (q.length < 3) return;
      var url =
        "https://photon.komoot.io/api/?q=" +
        encodeURIComponent(q) +
        "&limit=1&lang=en&lat=39.68&lon=-75.75";
      fetch(url)
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (data) {
          if (!data || !Array.isArray(data.features) || !data.features.length) {
            return;
          }
          var parsed = formatPhotonFeature(data.features[0]);
          if (parsed.lat != null && parsed.lon != null) {
            updatePlannerMapPin(
              isStartInput,
              parsed.lat,
              parsed.lon,
              parsed.name || q
            );
          }
        })
        .catch(function () {
          /* ignore offline lookup */
        });
    }

    function selectItem(item) {
      if (!item) return;
      cancelPendingFetch();
      menuLockedClosed = true;
      suppressNextInput = true;
      inputEl.value = item.name;
      closeMenu();
      if (item.lat != null && item.lon != null) {
        updatePlannerMapPin(isStartInput, item.lat, item.lon, item.name);
      } else {
        syncPinForText(item.name);
      }
      inputEl.dispatchEvent(new Event("input", { bubbles: true }));
      inputEl.dispatchEvent(new Event("change", { bubbles: true }));
      suppressNextInput = false;
      inputEl.blur();
    }

    function renderItems(items) {
      if (menuLockedClosed) {
        closeMenu();
        return;
      }
      currentItems = items;
      activeIdx = -1;
      listEl.innerHTML = "";
      if (!items.length) {
        closeMenu();
        return;
      }
      for (var i = 0; i < items.length; i += 1) {
        (function (idx, entry) {
          var opt = document.createElement("button");
          opt.type = "button";
          opt.className = "sc-autofill-item";
          opt.setAttribute("role", "option");
          var titleSpan = document.createElement("span");
          titleSpan.className = "sc-autofill-title";
          titleSpan.textContent = entry.title || entry.name;
          var metaSpan = document.createElement("span");
          metaSpan.className = "sc-autofill-meta";
          metaSpan.textContent = entry.meta || "";
          opt.appendChild(titleSpan);
          opt.appendChild(metaSpan);
          opt.addEventListener("mousedown", function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            selectItem(entry);
          });
          opt.addEventListener("click", function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            selectItem(entry);
          });
          listEl.appendChild(opt);
        })(i, items[i]);
      }
      listEl.style.display = "block";
    }

    function updateHighlight() {
      var opts = listEl.querySelectorAll(".sc-autofill-item");
      for (var i = 0; i < opts.length; i += 1) {
        opts[i].classList.toggle("sc-autofill-active", i === activeIdx);
      }
    }

    function localMatches(q) {
      var lower = (q || "").trim().toLowerCase();
      var out = [];
      for (var i = 0; i < catalog.length; i += 1) {
        var c = catalog[i];
        var hay = (c.name + " " + c.city + " " + c.category).toLowerCase();
        if (!lower || hay.indexOf(lower) !== -1) {
          out.push({
            name: c.name,
            title: c.name,
            meta: c.category + " · " + c.city,
            lat: c.lat,
            lon: c.lon,
          });
          if (out.length >= 6) break;
        }
      }
      return out;
    }

    function mergeUnique(primaryList, extraList) {
      var seen = {};
      var merged = [];
      var combined = primaryList.concat(extraList);
      for (var i = 0; i < combined.length; i += 1) {
        var key = String(combined[i].name || "").toLowerCase();
        if (!key || seen[key]) continue;
        seen[key] = true;
        merged.push(combined[i]);
        if (merged.length >= 6) break;
      }
      return merged;
    }

    function querySuggestions(rawQuery) {
      if (menuLockedClosed) return;
      var q = (rawQuery || "").trim();
      var locals = localMatches(q);
      renderItems(locals);
      if (q.length < 3) return;
      var cacheKey = q.toLowerCase();
      if (photonCache.has(cacheKey)) {
        renderItems(mergeUnique(locals, photonCache.get(cacheKey)));
        return;
      }
      cancelPendingFetch();
      debounceId = setTimeout(function () {
        if (menuLockedClosed) return;
        abortCtrl = new AbortController();
        var url =
          "https://photon.komoot.io/api/?q=" +
          encodeURIComponent(q) +
          "&limit=5&lang=en&lat=39.68&lon=-75.75";
        fetch(url, { signal: abortCtrl.signal })
          .then(function (r) {
            return r.ok ? r.json() : null;
          })
          .then(function (data) {
            if (menuLockedClosed) return;
            if (!data || !Array.isArray(data.features)) return;
            var remote = [];
            for (var i = 0; i < data.features.length; i += 1) {
              var parsed = formatPhotonFeature(data.features[i]);
              if (parsed.name) remote.push(parsed);
            }
            photonCache.set(cacheKey, remote);
            if (!menuLockedClosed && document.activeElement === inputEl) {
              renderItems(mergeUnique(localMatches(inputEl.value), remote));
            }
          })
          .catch(function () {
            /* ignore aborted or offline autocomplete fetch */
          });
      }, 210);
    }

    inputEl.addEventListener("focus", function () {
      menuLockedClosed = false;
      querySuggestions(inputEl.value);
    });
    inputEl.addEventListener("input", function () {
      if (suppressNextInput) return;
      menuLockedClosed = false;
      querySuggestions(inputEl.value);
    });
    inputEl.addEventListener("change", function () {
      if (suppressNextInput) return;
      syncPinForText(inputEl.value);
    });
    inputEl.addEventListener("blur", function () {
      setTimeout(closeMenu, 120);
    });
    document.addEventListener("mousedown", function (ev) {
      if (!host.contains(ev.target)) {
        closeMenu();
      }
    });
    inputEl.addEventListener("keydown", function (ev) {
      if (listEl.style.display === "none") {
        if (ev.key === "Enter") {
          syncPinForText(inputEl.value);
        }
        return;
      }
      if (ev.key === "ArrowDown") {
        ev.preventDefault();
        activeIdx = (activeIdx + 1) % currentItems.length;
        updateHighlight();
      } else if (ev.key === "ArrowUp") {
        ev.preventDefault();
        activeIdx =
          (activeIdx - 1 + currentItems.length) % currentItems.length;
        updateHighlight();
      } else if (ev.key === "Enter" && activeIdx >= 0) {
        ev.preventDefault();
        selectItem(currentItems[activeIdx]);
      } else if (ev.key === "Escape") {
        cancelPendingFetch();
        closeMenu();
      }
    });
  }

  function hydrateDynamicEnhancements() {
    syncBodyTheme();
    ensureBikeLoader();
    var inputs = document.querySelectorAll(
      'input[name="start_address"], input[name="dest_address"]'
    );
    for (var i = 0; i < inputs.length; i += 1) {
      attachLocationAutocomplete(inputs[i]);
    }
  }

  document.addEventListener(
    "click",
    function (ev) {
      var btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
      if (!btn || btn.__scBypassLoader) return;
      var text = (btn.innerText || "").trim();
      if (
        text.indexOf("Generate & Compare") !== -1 ||
        text === "Results"
      ) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        showBikeLoader("Mapping safer cycling routes...");
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            setTimeout(function () {
              btn.__scBypassLoader = true;
              btn.click();
              btn.__scBypassLoader = false;
            }, 32);
          });
        });
      }
    },
    true
  );

  var domObserver = new MutationObserver(function (mutations) {
    var shouldHide = false;
    for (var i = 0; i < mutations.length; i += 1) {
      var target = mutations[i].target;
      if (
        target &&
        target.closest &&
        (target.closest("#sc-bike-loader") ||
          target.closest(".sc-autofill-menu"))
      ) {
        continue;
      }
      if (mutations[i].addedNodes && mutations[i].addedNodes.length > 0) {
        for (var j = 0; j < mutations[i].addedNodes.length; j += 1) {
          var node = mutations[i].addedNodes[j];
          if (node && node.id === "sc-bike-loader") continue;
          if (
            node &&
            node.classList &&
            node.classList.contains("sc-autofill-menu")
          ) {
            continue;
          }
          shouldHide = true;
          break;
        }
      }
      if (shouldHide) break;
    }
    hydrateDynamicEnhancements();
    if (shouldHide) {
      hideBikeLoader(120);
    }
  });
  if (document.body) {
    domObserver.observe(document.body, { childList: true, subtree: true });
    hydrateDynamicEnhancements();
  }

  if (typeof customElements !== "undefined") {
    patchDrafterMapElement();
    customElements.whenDefined("drafter-map").then(patchDrafterMapElement);
  }
})();
"""

SAFECYCLE_CSS = """
:root {
  --sc-bg: #f8fafc;
  --sc-surface: #ffffff;
  --sc-surface-alt: #f1f5f9;
  --sc-border: #e2e8f0;
  --sc-text: #0f172a;
  --sc-muted: #475569;
  --sc-subtle: #64748b;
  --sc-brand: #047857;
  --sc-brand-hover: #065f46;
  --sc-brand-soft: #ecfdf5;
  --sc-danger: #b91c1c;
  --sc-danger-soft: #fef2f2;
  --sc-warn: #b45309;
  --sc-warn-soft: #fffbeb;
  --sc-radius: 10px;
}

*, *::before, *::after {
  box-sizing: border-box;
}

html, body {
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  background-color: var(--sc-bg);
  color: var(--sc-text);
  font-family: "DM Sans", system-ui, -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

html.sc-dark-root,
body.sc-dark-root {
  background-color: #0b1220;
  color: #f1f5f9;
}

.drafter-frame--,
#drafter-root--,
.drafter-body--,
.drafter-body-- > form,
.drafter-body-- > div,
.drafter-container,
.drafter-content,
.drafter-page,
.container,
body > div[id] {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent;
}

.sc-app-shell {
  width: 100%;
  min-height: 100vh;
  background-color: var(--sc-bg);
  color: var(--sc-text);
}

.sc-app-shell.sc-dark {
  --sc-bg: #0b1220;
  --sc-surface: #111827;
  --sc-surface-alt: #1e293b;
  --sc-border: #263245;
  --sc-text: #f1f5f9;
  --sc-muted: #cbd5e1;
  --sc-subtle: #94a3b8;
  --sc-brand: #10b981;
  --sc-brand-hover: #059669;
  --sc-brand-soft: #064e3b;
  --sc-danger: #f87171;
  --sc-danger-soft: #3b1219;
  --sc-warn: #fbbf24;
  --sc-warn-soft: #2e2108;
  background-color: var(--sc-bg);
  color: var(--sc-text);
}

/* Animated Bicycle Loading Screen (instant frame-1 start, smooth fade-out) */
.sc-bike-loader {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.92);
  backdrop-filter: blur(6px);
  color: #0f172a;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateZ(0);
}

.sc-bike-loader.sc-dark {
  background: rgba(11, 18, 32, 0.92);
  color: #f1f5f9;
  --sc-brand: #10b981;
}

.sc-bike-loader.sc-loader-visible {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transition: none;
}

.sc-bike-loader.sc-loader-hidden {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 180ms ease, visibility 180ms ease;
}

.sc-bike-loader-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 28px 36px;
  border-radius: 14px;
  background: var(--sc-surface);
  border: 1px solid var(--sc-border);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
}

.sc-bike-loader.sc-dark .sc-bike-loader-card {
  background: #111827;
  border-color: #263245;
}

.sc-bike-loader-title {
  font-family: "Plus Jakarta Sans", system-ui, sans-serif;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--sc-brand);
  letter-spacing: -0.02em;
}

.sc-bike-loader-sub {
  font-size: 0.88rem;
  color: var(--sc-muted);
}

.sc-bike-loader.sc-dark .sc-bike-loader-sub {
  color: #cbd5e1;
}

.sc-bike-stage {
  position: relative;
  width: 140px;
  height: 82px;
  overflow: hidden;
  transform: translateZ(0);
}

.sc-road-clip {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  height: 3px;
  overflow: hidden;
}

.sc-road-track {
  position: absolute;
  left: 0;
  top: 0;
  width: 220px;
  height: 3px;
  background-image: repeating-linear-gradient(
    to right,
    currentColor 0px,
    currentColor 10px,
    transparent 10px,
    transparent 20px
  );
  opacity: 0.28;
  will-change: transform;
  backface-visibility: hidden;
  animation: sc-road-slide 0.55s linear infinite;
}

.sc-bike-body {
  position: absolute;
  inset: 0;
  will-change: transform;
  backface-visibility: hidden;
  animation: sc-bike-bob 0.6s ease-in-out infinite alternate;
}

.sc-frame-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.sc-wheel-layer {
  position: absolute;
  width: 38px;
  height: 38px;
  top: 35px;
  will-change: transform;
  backface-visibility: hidden;
  animation: sc-wheel-spin 0.78s linear infinite;
}

.sc-wheel-rear {
  left: 15px;
}

.sc-wheel-front {
  left: 85px;
}

@keyframes sc-wheel-spin {
  from { transform: rotate(0deg) translateZ(0); }
  to { transform: rotate(360deg) translateZ(0); }
}

@keyframes sc-bike-bob {
  from { transform: translate3d(0, 0px, 0); }
  to { transform: translate3d(0, -2.5px, 0); }
}

@keyframes sc-road-slide {
  from { transform: translate3d(0px, 0, 0); }
  to { transform: translate3d(-20px, 0, 0); }
}

@media (prefers-reduced-motion: reduce) {
  .sc-wheel-rear,
  .sc-wheel-front,
  .sc-bike-body,
  .sc-road-track {
    animation: none !important;
  }
}

h1, h2, h3, h4 {
  font-family: "Plus Jakarta Sans", system-ui, sans-serif;
  color: var(--sc-text);
  margin: 0 0 8px 0;
  line-height: 1.25;
  text-wrap: balance;
}

h1 { font-size: clamp(1.75rem, 3vw, 2.35rem); font-weight: 800; letter-spacing: -0.025em; }
h2 { font-size: 1.3rem; font-weight: 700; letter-spacing: -0.015em; }
h3 { font-size: 1.05rem; font-weight: 700; }

p { margin: 0 0 10px 0; color: var(--sc-muted); }

/* 3-zone Top Bar */
.sc-topbar {
  background: var(--sc-surface);
  border-bottom: 1px solid var(--sc-border);
  position: sticky;
  top: 0;
  z-index: 40;
}

.sc-topbar-inner {
  max-width: 1240px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
}

.sc-topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.sc-brand-btn {
  background: transparent !important;
  border: none !important;
  padding: 4px 0 !important;
  font-family: "Plus Jakarta Sans", sans-serif !important;
  font-size: 1.2rem !important;
  font-weight: 800 !important;
  color: var(--sc-brand) !important;
  letter-spacing: -0.02em;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  box-shadow: none !important;
}

.sc-nav-links {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

.sc-nav-btn {
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  padding: 8px 12px !important;
  font-family: "DM Sans", sans-serif !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  color: var(--sc-muted) !important;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: color 150ms ease, border-color 150ms ease;
}

.sc-nav-btn:hover {
  color: var(--sc-text) !important;
}

.sc-nav-btn.sc-nav-active {
  color: var(--sc-brand) !important;
  border-bottom-color: var(--sc-brand) !important;
}

.sc-theme-toggle {
  width: 38px !important;
  height: 38px !important;
  min-height: 38px !important;
  padding: 0 !important;
  font-size: 1.08rem !important;
  line-height: 1 !important;
  border-radius: 8px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: var(--sc-text) !important;
  background: var(--sc-surface) !important;
  border: 1px solid var(--sc-border) !important;
}

.sc-theme-toggle:hover {
  background: var(--sc-surface-alt) !important;
  border-color: var(--sc-brand) !important;
}

.sc-container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 48px 24px;
}

/* Primary surfaces */
.sc-panel {
  position: relative;
  z-index: 2;
  background: var(--sc-surface);
  border: 1px solid var(--sc-border);
  border-radius: var(--sc-radius);
  padding: 22px;
  margin-bottom: 18px;
}

.sc-panel:hover,
.sc-panel:focus-within {
  z-index: 35;
}

.sc-panel-compact {
  padding: 18px;
  margin-bottom: 0;
}

.sc-panel-muted {
  background: var(--sc-surface-alt);
  border: 1px solid var(--sc-border);
  border-radius: var(--sc-radius);
  padding: 18px;
  margin-bottom: 18px;
}

/* Card Header + Top-Right Question Mark Hover Tooltip */
.sc-card-head-row {
  position: relative;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.sc-card-head-row h1,
.sc-card-head-row h2,
.sc-card-head-row h3 {
  margin: 0;
}

.sc-map-toolbar {
  position: relative;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.sc-map-toolbar .sc-map-legend {
  margin: 0;
}

.sc-help-tip {
  position: relative;
  z-index: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--sc-border);
  background: var(--sc-surface-alt);
  color: var(--sc-subtle);
  font-family: "Plus Jakarta Sans", system-ui, sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: help;
  flex-shrink: 0;
  user-select: none;
  transition: border-color 150ms ease, color 150ms ease, background-color 150ms ease;
}

.sc-help-tip:hover,
.sc-help-tip:focus-visible {
  border-color: var(--sc-brand);
  color: var(--sc-brand);
  background: var(--sc-brand-soft);
  outline: none;
}

.sc-help-bubble {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 270px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #f8fafc;
  font-family: "DM Sans", system-ui, sans-serif;
  font-size: 0.8rem;
  font-weight: 400;
  line-height: 1.45;
  text-align: left;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.28);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-3px);
  pointer-events: none;
  z-index: 9999;
  transition: opacity 150ms ease, transform 150ms ease, visibility 150ms ease;
}

.sc-dark .sc-help-bubble {
  background: #1e293b;
  color: #f1f5f9;
  border: 1px solid #334155;
}

.sc-help-tip:hover .sc-help-bubble,
.sc-help-tip:focus-visible .sc-help-bubble {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.sc-split-2 {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: 22px;
  align-items: stretch;
}

.sc-results-split {
  display: grid;
  grid-template-columns: minmax(0, 1.32fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
  margin-bottom: 18px;
}

.sc-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.sc-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.sc-grid-4 {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

/* Planner Start/End Group with Compact Swap Icon Button */
.sc-endpoints-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.sc-endpoints-inputs {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sc-endpoints-inputs .sc-field {
  margin-bottom: 0;
}

.sc-swap-icon-btn {
  width: 36px !important;
  height: 36px !important;
  min-height: 36px !important;
  padding: 0 !important;
  margin-top: 22px;
  border-radius: 50% !important;
  border: 1px solid var(--sc-border) !important;
  background: var(--sc-surface-alt) !important;
  color: var(--sc-muted) !important;
  font-size: 1rem !important;
  line-height: 1 !important;
  flex-shrink: 0;
  transition: transform 160ms ease, border-color 150ms ease, color 150ms ease,
    background-color 150ms ease !important;
}

.sc-swap-icon-btn:hover {
  border-color: var(--sc-brand) !important;
  color: var(--sc-brand) !important;
  background: var(--sc-brand-soft) !important;
  transform: rotate(180deg);
}

/* Integrated Sleek Underline Route Switcher Tabs (1-3 routes) */
.sc-route-tabs {
  display: flex;
  align-items: stretch;
  gap: 4px;
  border-bottom: 1px solid var(--sc-border);
  margin: -6px -18px 16px -18px;
  padding: 0 18px;
}

.sc-route-tab {
  flex: 1 1 0;
  min-width: 0;
  min-height: 38px !important;
  padding: 8px 6px 10px 6px !important;
  font-size: 0.85rem !important;
  font-weight: 600 !important;
  border: none !important;
  border-bottom: 2.5px solid transparent !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--sc-subtle) !important;
  margin-bottom: -1px;
  box-shadow: none !important;
  transition: color 140ms ease, border-color 140ms ease;
}

.sc-route-tab:hover {
  background: transparent !important;
  color: var(--sc-text) !important;
  border-bottom-color: var(--sc-border) !important;
}

.sc-route-tab.sc-route-tab-active {
  background: transparent !important;
  color: var(--sc-brand) !important;
  font-weight: 700 !important;
  border-bottom-color: var(--sc-brand) !important;
}

.sc-selected-route-box {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sc-route-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sc-route-card-score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
  text-align: right;
  flex-shrink: 0;
}

.sc-score-bar-track {
  width: 96px;
  height: 6px;
  border-radius: 99px;
  background: var(--sc-surface-alt);
  border: 1px solid var(--sc-border);
  overflow: hidden;
  margin-top: 2px;
}

.sc-score-bar-fill {
  height: 100%;
  border-radius: 99px;
}

/* Prominent Hero Trip Statistics Grid (Distance, Time, Elevation) */
.sc-trip-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.sc-trip-stat {
  background: var(--sc-surface-alt);
  border: 1px solid var(--sc-border);
  border-radius: 9px;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sc-trip-stat-val {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--sc-text);
  line-height: 1.2;
}

.sc-trip-stat-lbl {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--sc-subtle);
}

/* Highlighted Bike Infrastructure Feature Block */
.sc-infra-highlight {
  background: var(--sc-brand-soft);
  border: 1px solid rgba(4, 120, 87, 0.25);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sc-dark .sc-infra-highlight {
  border-color: rgba(16, 185, 129, 0.35);
}

.sc-infra-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.sc-infra-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--sc-brand);
  letter-spacing: 0.01em;
}

.sc-infra-pct {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 1.12rem;
  font-weight: 800;
  color: var(--sc-brand);
}

.sc-infra-track {
  width: 100%;
  height: 7px;
  border-radius: 99px;
  background: rgba(15, 23, 42, 0.1);
  overflow: hidden;
}

.sc-dark .sc-infra-track {
  background: rgba(255, 255, 255, 0.14);
}

.sc-infra-fill {
  height: 100%;
  border-radius: 99px;
  background: var(--sc-brand);
}

.sc-infra-sub {
  font-size: 0.78rem;
  color: var(--sc-muted);
}

.sc-route-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--sc-border);
}

.sc-route-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 10px 0;
  border-top: 1px solid var(--sc-border);
  border-bottom: 1px solid var(--sc-border);
}

.sc-route-metric-item {
  display: flex;
  flex-direction: column;
}

.sc-route-metric-val {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--sc-text);
}

.sc-route-metric-lbl {
  font-size: 0.72rem;
  color: var(--sc-subtle);
}

.sc-route-rationale {
  font-size: 0.87rem;
  color: var(--sc-muted);
  margin: 0;
  line-height: 1.5;
}

.sc-compact-warnings {
  background: var(--sc-warn-soft);
  border: 1px solid var(--sc-warn);
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 10px;
  font-size: 0.83rem;
}

.sc-compact-warnings ul {
  margin: 4px 0 0 0;
  padding-left: 18px;
}

.sc-mono {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}

.sc-kpi-value {
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--sc-text);
  line-height: 1.15;
}

.sc-kpi-label {
  font-size: 0.78rem;
  color: var(--sc-subtle);
  margin-top: 2px;
}

.sc-meta-line {
  font-size: 0.82rem;
  color: var(--sc-subtle);
}

/* Risk text semantics */
.sc-risk-lower { color: #15803d; font-weight: 700; }
.sc-risk-moderate { color: #b45309; font-weight: 700; }
.sc-risk-elevated { color: #c2410c; font-weight: 700; }
.sc-risk-high { color: #b91c1c; font-weight: 700; }
.sc-risk-unknown { color: #64748b; font-weight: 700; }

.sc-dark .sc-risk-lower { color: #4ade80; }
.sc-dark .sc-risk-moderate { color: #fbbf24; }
.sc-dark .sc-risk-elevated { color: #fb923c; }
.sc-dark .sc-risk-high { color: #f87171; }
.sc-dark .sc-risk-unknown { color: #94a3b8; }

/* Notices & Alerts */
.sc-notice {
  background: var(--sc-brand-soft);
  border: 1px solid var(--sc-brand);
  color: var(--sc-text);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 18px;
  font-size: 0.92rem;
}

.sc-warning-box {
  background: var(--sc-warn-soft);
  border: 1px solid var(--sc-warn);
  color: var(--sc-text);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 18px;
  font-size: 0.9rem;
}

.sc-danger-box {
  background: var(--sc-danger-soft);
  border: 1px solid var(--sc-danger);
  color: var(--sc-text);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 18px;
  font-size: 0.9rem;
}

/* Location Autofill Dropdown */
.sc-autofill-host {
  position: relative;
}

.sc-autofill-menu {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  z-index: 60;
  background: var(--sc-surface);
  border: 1px solid var(--sc-border);
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.14);
  overflow: hidden;
  max-height: 270px;
  overflow-y: auto;
}

.sc-autofill-item {
  width: 100% !important;
  min-height: 44px !important;
  padding: 8px 12px !important;
  border: none !important;
  border-bottom: 1px solid var(--sc-border) !important;
  border-radius: 0 !important;
  background: var(--sc-surface) !important;
  color: var(--sc-text) !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  justify-content: center !important;
  text-align: left !important;
  gap: 2px !important;
  white-space: normal !important;
  cursor: pointer;
}

.sc-autofill-item:last-child {
  border-bottom: none !important;
}

.sc-autofill-item:hover,
.sc-autofill-item.sc-autofill-active {
  background: var(--sc-surface-alt) !important;
}

.sc-autofill-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--sc-text);
}

.sc-autofill-meta {
  font-size: 0.76rem;
  color: var(--sc-subtle);
}

/* Form controls */
label {
  display: block;
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--sc-text);
  margin-bottom: 5px;
}

input[type="text"],
input[type="number"],
input[type="time"],
select,
textarea {
  width: 100%;
  padding: 9px 12px;
  font-family: "DM Sans", sans-serif;
  font-size: 0.94rem;
  color: var(--sc-text);
  background: var(--sc-surface);
  border: 1px solid var(--sc-border);
  border-radius: 8px;
  outline: none;
  transition: border-color 150ms ease;
}

input[type="text"]:focus,
input[type="number"]:focus,
input[type="time"]:focus,
select:focus,
textarea:focus {
  border-color: var(--sc-brand);
  box-shadow: 0 0 0 3px rgba(4, 120, 87, 0.14);
}

input[type="checkbox"] {
  width: 17px;
  height: 17px;
  accent-color: var(--sc-brand);
  cursor: pointer;
}

.sc-field {
  margin-bottom: 14px;
}

/* Buttons & Download links */
button,
input[type="submit"],
a.sc-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 18px;
  min-height: 40px;
  font-family: "DM Sans", sans-serif;
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.2;
  border-radius: 8px;
  border: 1px solid var(--sc-border);
  background: var(--sc-surface);
  color: var(--sc-text);
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
}

button:hover,
a.sc-btn:hover {
  background: var(--sc-surface-alt);
}

button:focus-visible,
a.sc-btn:focus-visible {
  outline: 2px solid var(--sc-brand);
  outline-offset: 2px;
}

.sc-btn-primary {
  background: var(--sc-brand) !important;
  border-color: var(--sc-brand) !important;
  color: #ffffff !important;
}

.sc-btn-primary:hover {
  background: var(--sc-brand-hover) !important;
  border-color: var(--sc-brand-hover) !important;
}

.sc-btn-sm {
  padding: 6px 12px !important;
  min-height: 36px !important;
  font-size: 0.83rem !important;
}

.sc-btn-full {
  width: 100%;
}

.sc-btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

/* Native HTML5 Meter */
meter, progress {
  width: 100%;
  height: 8px;
  border-radius: 6px;
  overflow: hidden;
  accent-color: var(--sc-brand);
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th {
  text-align: left;
  padding: 10px 12px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--sc-subtle);
  border-bottom: 2px solid var(--sc-border);
  background: var(--sc-surface-alt);
}

td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--sc-border);
  vertical-align: middle;
  color: var(--sc-text);
}

tbody tr:hover td {
  background: var(--sc-surface-alt);
}

tr:last-child td {
  border-bottom: none;
}

/* Details accordion */
details {
  border: 1px solid var(--sc-border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 12px;
  background: var(--sc-surface-alt);
}

summary {
  font-weight: 600;
  cursor: pointer;
  color: var(--sc-text);
}

svg {
  max-width: 100%;
  height: auto;
  display: block;
}

drafter-map {
  display: block;
  position: relative;
  z-index: 1;
  isolation: isolate;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--sc-border);
}

.sc-map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 12px;
  align-items: center;
  font-size: 0.77rem;
  color: var(--sc-muted);
  margin: 10px 0 14px 0;
}

.sc-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sc-legend-swatch {
  display: inline-block;
  width: 14px;
  height: 4px;
  border-radius: 2px;
}

.sc-check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.sc-check-row label {
  margin-bottom: 0;
  font-weight: 500;
  cursor: pointer;
}

.sc-footer {
  border-top: 1px solid var(--sc-border);
  padding: 20px 24px;
  margin-top: 32px;
  font-size: 0.82rem;
  color: var(--sc-subtle);
  text-align: center;
}

@media (max-width: 960px) {
  .sc-split-2,
  .sc-results-split,
  .sc-grid-3,
  .sc-grid-4,
  .sc-grid-2 {
    grid-template-columns: 1fr;
  }
  .sc-topbar-inner {
    flex-wrap: wrap;
    gap: 12px;
    padding: 10px 16px;
  }
  .sc-nav-links {
    overflow-x: auto;
    max-width: 100%;
  }
  .sc-container {
    padding: 18px 16px 36px 16px;
  }
}
"""
