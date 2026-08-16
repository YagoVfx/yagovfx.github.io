/*
 * FASE 2 — Escena 3D estática (sin interacción todavía)
 * =======================================================
 *
 * Objetivo de esta fase: validar que la habitación carga rápido y se ve
 * bien con una cámara fija, ANTES de invertir tiempo en libros
 * interactivos, coreografía de cámara o materiales detallados.
 *
 * Decisiones deliberadas para esta fase (ya acordadas):
 *   - Solo geometría primitiva de Three.js (cajas, cilindros, planos) —
 *     nada de modelos 3D importados. Evita producción de assets pesada.
 *   - Solo sombras básicas (PCFSoftShadowMap). Nada de luz volumétrica,
 *     polvo, profundidad de campo ni post-procesado — eso es la Fase 11.
 *   - Sin libros como objetos independientes todavía — eso es la Fase 3.
 *   - Cámara fija, sin animación — eso es la Fase 5.
 *
 * Contrato con index.html: exporta initLibraryScene(container), que
 * devuelve { pause(), resume() }. index.html se encarga de cuándo
 * llamarlas (visibilidad de la skin) — este archivo no sabe nada del
 * resto de la web ni del SkinManager.
 */

import * as THREE from 'three';

export async function initLibraryScene(container) {
  let running = true;
  let rafId = null;

  // ── Renderer ──────────────────────────────────────────────────────
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap; // sombras suaves básicas, coste bajo
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  // ── Escena y cámara ───────────────────────────────────────────────
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a140e);
  scene.fog = new THREE.Fog(0x1a140e, 8, 22);

  const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    100
  );
  // Encuadre fijo: como si alguien acabara de entrar en la habitación,
  // mirando hacia la estantería y la mesa. Se refinará en la Fase 5
  // cuando exista la máquina de estados de cámara.
  camera.position.set(0, 1.6, 6.5);
  camera.lookAt(0, 1.3, 0);

  // ── Materiales base (tonos cálidos, madera/tela) ─────────────────
  const woodMat = new THREE.MeshStandardMaterial({ color: 0x6b4a30, roughness: 0.8, metalness: 0.05 });
  const woodDarkMat = new THREE.MeshStandardMaterial({ color: 0x3f2a1c, roughness: 0.85, metalness: 0.05 });
  const wallMat = new THREE.MeshStandardMaterial({ color: 0x2b2118, roughness: 0.95 });
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x4a3320, roughness: 0.7 });
  const fabricMat = new THREE.MeshStandardMaterial({ color: 0x5a4636, roughness: 0.9 });
  const shadeMat = new THREE.MeshStandardMaterial({ color: 0xe8c98a, roughness: 0.6, emissive: 0x3a2c14, emissiveIntensity: 0.4 });
  const leafMat = new THREE.MeshStandardMaterial({ color: 0x3f5a3a, roughness: 0.8 });
  const potMat = new THREE.MeshStandardMaterial({ color: 0x7a4a35, roughness: 0.9 });

  // ── Habitación (suelo, techo, 3 paredes — sin la del visitante) ───
  const room = new THREE.Group();

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  room.add(floor);

  const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), wallMat);
  ceiling.rotation.x = Math.PI / 2;
  ceiling.position.y = 3.2;
  room.add(ceiling);

  const backWall = new THREE.Mesh(new THREE.PlaneGeometry(10, 3.2), wallMat);
  backWall.position.set(0, 1.6, -3);
  room.add(backWall);

  const leftWall = new THREE.Mesh(new THREE.PlaneGeometry(6, 3.2), wallMat);
  leftWall.rotation.y = Math.PI / 2;
  leftWall.position.set(-5, 1.6, 0);
  room.add(leftWall);

  const rightWall = new THREE.Mesh(new THREE.PlaneGeometry(6, 3.2), wallMat);
  rightWall.rotation.y = -Math.PI / 2;
  rightWall.position.set(5, 1.6, 0);
  room.add(rightWall);

  scene.add(room);

  // ── Ventana (en la pared derecha, fuente de luz principal) ────────
  const windowFrame = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 2), new THREE.MeshStandardMaterial({
    color: 0xcfe0e8, roughness: 0.3, emissive: 0x8fa8b8, emissiveIntensity: 0.5,
  }));
  windowFrame.position.set(4.98, 1.8, -0.5);
  windowFrame.rotation.y = -Math.PI / 2;
  scene.add(windowFrame);

  // ── Estantería (solo estructura — SIN libros, eso es la Fase 3) ──
  const shelf = new THREE.Group();
  const shelfWidth = 3.4, shelfHeight = 2.6, shelfDepth = 0.4;
  const shelfSideGeo = new THREE.BoxGeometry(0.08, shelfHeight, shelfDepth);
  const shelfSideL = new THREE.Mesh(shelfSideGeo, woodDarkMat);
  shelfSideL.position.set(-shelfWidth / 2, shelfHeight / 2, 0);
  const shelfSideR = shelfSideL.clone();
  shelfSideR.position.x = shelfWidth / 2;
  shelf.add(shelfSideL, shelfSideR);

  const shelfBoardGeo = new THREE.BoxGeometry(shelfWidth, 0.06, shelfDepth);
  const shelfLevels = 4;
  for (let i = 0; i <= shelfLevels; i++) {
    const board = new THREE.Mesh(shelfBoardGeo, woodMat);
    board.position.set(0, (shelfHeight / shelfLevels) * i, 0);
    board.castShadow = true;
    board.receiveShadow = true;
    shelf.add(board);
  }
  shelf.position.set(-3.2, 0, -2.7);
  scene.add(shelf);

  // ── Mesa ────────────────────────────────────────────────────────
  const desk = new THREE.Group();
  const deskTop = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.08, 1.1), woodMat);
  deskTop.position.y = 0.9;
  deskTop.castShadow = true;
  deskTop.receiveShadow = true;
  desk.add(deskTop);
  const legGeo = new THREE.BoxGeometry(0.08, 0.9, 0.08);
  const legOffsets = [[-1.1, -0.48], [1.1, -0.48], [-1.1, 0.48], [1.1, 0.48]];
  legOffsets.forEach(([x, z]) => {
    const leg = new THREE.Mesh(legGeo, woodDarkMat);
    leg.position.set(x, 0.45, z);
    leg.castShadow = true;
    desk.add(leg);
  });
  desk.position.set(1.2, 0, 0.5);
  scene.add(desk);

  // ── Silla (muy simple: asiento + respaldo + una pata central) ────
  const chair = new THREE.Group();
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.06, 0.55), fabricMat);
  seat.position.y = 0.5;
  seat.castShadow = true;
  chair.add(seat);
  const back = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.6, 0.06), fabricMat);
  back.position.set(0, 0.8, -0.26);
  back.castShadow = true;
  chair.add(back);
  const chairLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.5, 8), woodDarkMat);
  chairLeg.position.y = 0.25;
  chair.add(chairLeg);
  chair.position.set(1.2, 0, 1.6);
  scene.add(chair);

  // ── Lámpara de mesa (con su propia luz puntual cálida) ───────────
  const lamp = new THREE.Group();
  const lampBase = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.04, 12), woodDarkMat);
  lamp.add(lampBase);
  const lampArm = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.5, 8), woodDarkMat);
  lampArm.position.y = 0.27;
  lamp.add(lampArm);
  const lampShade = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.22, 12, 1, true), shadeMat);
  lampShade.position.y = 0.55;
  lamp.add(lampShade);
  const lampLight = new THREE.PointLight(0xffcf8a, 6, 4, 2);
  lampLight.position.y = 0.5;
  lampLight.castShadow = false; // una sola luz con sombra basta para esta fase (rendimiento)
  lamp.add(lampLight);
  lamp.position.set(0.3, 0.94, 0.5);
  desk.add(lamp);

  // ── Un par de plantas (geometría muy simple) ──────────────────────
  function makePlant(x, z, scale = 1) {
    const plant = new THREE.Group();
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.14, 0.22, 10), potMat);
    pot.position.y = 0.11;
    pot.castShadow = true;
    plant.add(pot);
    const foliage = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28, 0), leafMat);
    foliage.position.y = 0.45;
    foliage.scale.set(1, 1.3, 1);
    foliage.castShadow = true;
    plant.add(foliage);
    plant.position.set(x, 0, z);
    plant.scale.setScalar(scale);
    return plant;
  }
  scene.add(makePlant(-4.4, 1.8, 1.15));
  scene.add(makePlant(3.6, -2.2, 0.9));

  // ── Iluminación ────────────────────────────────────────────────────
  const ambient = new THREE.AmbientLight(0x8899aa, 0.35);
  scene.add(ambient);

  // Luz principal: entra por la ventana. Es la única que proyecta
  // sombra por ahora — mantiene el coste de renderizado bajo.
  const windowLight = new THREE.DirectionalLight(0xcfe0e8, 1.1);
  windowLight.position.set(4.5, 3, 1);
  windowLight.target.position.set(0, 0, 0);
  windowLight.castShadow = true;
  windowLight.shadow.mapSize.set(1024, 1024);
  windowLight.shadow.camera.left = -6;
  windowLight.shadow.camera.right = 6;
  windowLight.shadow.camera.top = 6;
  windowLight.shadow.camera.bottom = -6;
  windowLight.shadow.camera.far = 15;
  scene.add(windowLight);
  scene.add(windowLight.target);

  // Luz de relleno cálida general (sin sombra) para que no queden zonas
  // completamente negras — mantiene el ambiente "acogedor" sin coste.
  const fill = new THREE.PointLight(0xffb877, 1.2, 8, 2);
  fill.position.set(-2, 2.2, 1);
  scene.add(fill);

  // ── Resize ──────────────────────────────────────────────────────
  function onResize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  const resizeObserver = new ResizeObserver(onResize);
  resizeObserver.observe(container);

  // ── Loop de render ─────────────────────────────────────────────
  function tick() {
    if (!running) return;
    renderer.render(scene, camera);
    rafId = requestAnimationFrame(tick);
  }
  tick();

  // Pausa el render si la pestaña no está visible, aunque la skin siga
  // activa — evita gastar GPU en segundo plano sin motivo.
  function onVisibilityChange() {
    if (document.hidden) pause();
    else if (running === false && container.style.display !== 'none') resume();
  }
  document.addEventListener('visibilitychange', onVisibilityChange);

  function pause() {
    running = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
  }
  function resume() {
    if (running) return;
    running = true;
    onResize(); // el contenedor pudo cambiar de tamaño mientras estaba oculto
    tick();
  }

  return { pause, resume };
}
