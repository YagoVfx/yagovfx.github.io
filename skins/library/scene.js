/*
 * FASE 3 — Estantería generada por datos
 * =========================================
 *
 * Sobre la Fase 2 (habitación estática), esta fase añade: los libros se
 * generan automáticamente a partir de `books` (viene de
 * sections-model.js / deriveSectionsModel), no están hardcodeados en la
 * escena. Añadir o quitar una sección en los datos reordena la
 * estantería sola, sin tocar este archivo.
 *
 * Todavía NO hay interacción (hover/click) — eso es la Fase 4. Los
 * libros son mallas simples (cajas) con color/grosor derivados de los
 * datos; personalidad visual real (texturas, desgaste, tipografía del
 * lomo) es la Fase 10.
 *
 * Decisiones ya acordadas y vigentes desde la Fase 2:
 *   - Solo geometría primitiva de Three.js — nada de modelos 3D importados.
 *   - Solo sombras básicas (PCFSoftShadowMap).
 *   - Cámara fija, sin animación — eso es la Fase 5.
 *
 * Contrato con index.html: exporta initLibraryScene(container, books),
 * que devuelve { pause(), resume(), books }. `books` (los meshes 3D, no
 * los datos) se expone para que fases futuras (hover en Fase 4, click
 * en Fase 5) puedan engancharse sin tener que rehacer la generación.
 */

import * as THREE from 'three';

export async function initLibraryScene(container, books = []) {
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

  // ── Estantería (estructura fija + libros generados por datos) ────
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

  // ── Libros (Fase 3): generados a partir de `books`, no hardcodeados.
  // Cada libro es una simple caja — nada de modelado, personalidad
  // visual real (texturas, desgaste, tipografía del lomo) es la Fase 10.
  // El único "carácter" que se les da ahora es grosor y color, ambos
  // calculados a partir de los propios datos (pageCount, índice), para
  // que se distingan de un vistazo sin haber diseñado cada uno a mano.
  const bookPalette = [0xa63d2f, 0x3d5a80, 0x6b8f3f, 0xb08a3e, 0x7a4a8f, 0x2e6b6b, 0x9c4a5c];
  const shelfInnerWidth = shelfWidth - 0.2; // deja margen a los laterales
  const bookHeight = (shelfHeight / shelfLevels) - 0.12; // cabe entre dos baldas
  const bookDepth = shelfDepth - 0.08;

  const bookGroups = []; // se guarda para reutilizar en fases futuras (hover/click)
  let level = 0;
  const halfInnerWidth = shelfInnerWidth / 2;
  let cursorX = -halfInnerWidth;

  books.forEach((book, i) => {
    let thickness = Math.min(0.05 + (book.pageCount || 1) * 0.012, 0.16);

    // Si no cabe en la balda actual, salta a la siguiente (envoltura
    // automática — así añadir un libro de más no rompe el layout).
    if (cursorX + thickness > halfInnerWidth && level < shelfLevels - 1) {
      level++;
      cursorX = -halfInnerWidth;
    }

    // Caso límite (muchos más libros de los que caben físicamente,
    // incluso repartidos en todas las baldas): se estrecha el libro para
    // que quede dentro del hueco, en vez de dejar que atraviese la
    // estructura de la estantería. Solo ocurre con muchas más secciones
    // de las que este portfolio tendrá nunca, pero así el layout nunca
    // se rompe visualmente por muy grande que crezca el contenido.
    const remaining = halfInnerWidth - cursorX;
    if (remaining < thickness) thickness = Math.max(remaining, 0.005);

    const color = bookPalette[i % bookPalette.length];
    const bookMat = new THREE.MeshStandardMaterial({ color, roughness: 0.75, metalness: 0.02 });
    const bookMesh = new THREE.Mesh(new THREE.BoxGeometry(thickness, bookHeight, bookDepth), bookMat);
    bookMesh.castShadow = true;
    bookMesh.receiveShadow = true;
    bookMesh.userData = { bookId: book.id, title: book.title, shortLabel: book.shortLabel };

    const y = (shelfHeight / shelfLevels) * level + bookHeight / 2 + 0.03;
    bookMesh.position.set(cursorX + thickness / 2, y, 0);
    shelf.add(bookMesh);
    bookGroups.push(bookMesh);

    // El cursor nunca puede superar el límite físico de la balda, ni
    // para este libro ni para calcular la posición del siguiente — es
    // la parte clave del blindaje, no solo acotar el grosor de uno.
    cursorX = Math.min(cursorX + thickness + 0.01, halfInnerWidth);
  });

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

  return { pause, resume, books: bookGroups };
}
