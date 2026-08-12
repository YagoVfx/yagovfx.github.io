/*
 * FASE 0 — deriveSectionsModel(D)
 * ================================
 *
 * Esto NO sustituye a D. Es una capa de lectura, pura (sin efectos
 * secundarios), que transforma el mismo objeto D que ya usa Classic hoy
 * en el esquema "sections.json" que definimos en la arquitectura, para
 * que la skin Library (y cualquier skin futura) tenga algo consistente
 * que consumir sin tener que entender la forma interna de D.
 *
 * Classic sigue funcionando exactamente igual — esta función no se llama
 * desde ningún sitio de Classic, es aditiva. Riesgo de romper algo
 * existente: cero, porque no se toca ningún render*() actual.
 *
 * Distingue explícitamente entre:
 *   - "books"       -> objetos con la coreografía completa (sacar de la
 *                       estantería, mover a la mesa, abrir, leer)
 *   - "deskObjects" -> objetos más ligeros ya presentes en la mesa
 *                       (CV como carpeta, VFX Jobs como consola/monitor)
 *
 * Decisiones de diseño ya tomadas y reflejadas aquí:
 *   - Experiencia = UN libro ("reel"), cada empresa es un capítulo/página
 *     dentro, no un libro por empresa.
 *   - CV/Resume = objeto de mesa (carpeta), no libro.
 *   - VFX Jobs = objeto de mesa (consola/monitor), no libro ni libro con
 *     páginas — ya se decidió como caso especial en la arquitectura.
 *   - Un libro con 0 contenido real (ej. Devlog sin posts todavía) no se
 *     muestra en la estantería — evita libros "vacíos" sin propósito,
 *     coherente con "no quiero demasiados objetos sin sentido" del brief.
 */

function deriveSectionsModel(D) {
  const books = [];

  // Libro: Reel & Experience
  // Página de portada con el perfil, y una página/capítulo por empresa.
  const reelPages = [
    {
      type: 'cover',
      data: {
        name: D.profile && D.profile.name,
        role: D.profile && D.profile.role,
        bio: D.profile && D.profile.bio,
        stats: [
          { n: D.profile && D.profile.s1n, l: D.profile && D.profile.s1l },
          { n: D.profile && D.profile.s2n, l: D.profile && D.profile.s2l },
          { n: D.profile && D.profile.s3n, l: D.profile && D.profile.s3l },
        ].filter(function (s) { return s.n; }),
        reel: (D.reel && D.reel.enabled) ? { title: D.reel.title, video: D.reel.video, thumb: D.reel.thumb } : null,
      },
    },
  ].concat((D.companies || []).map(function (co) {
    return {
      type: 'company',
      data: {
        id: co.id,
        name: co.name,
        role: co.role,
        period: co.period,
        engine: co.engine,
        tools: co.tools,
        desc: co.desc,
        logo: co.logo,
        thumb: co.thumb,
        clips: co.clips || [],
      },
    };
  }));

  if (reelPages.length > 1 || (D.profile && D.profile.name)) {
    books.push({
      id: 'reel',
      type: 'book',
      title: 'Show Reel & Experience',
      shortLabel: 'Reel',
      pageCount: reelPages.length,
      pages: reelPages,
    });
  }

  // Libro: Tools & Software
  if ((D.tools || []).length > 0) {
    books.push({
      id: 'tools',
      type: 'book',
      title: 'Tools & Software',
      shortLabel: 'Tools',
      pageCount: 1,
      pages: [{ type: 'tools-grid', data: { tools: D.tools } }],
    });
  }

  // Libro: Devlog — solo aparece si hay al menos un post publicado; un
  // libro vacío no tiene propósito (principio del brief original).
  if ((D.posts || []).length > 0) {
    books.push({
      id: 'devlog',
      type: 'book',
      title: 'Devlog',
      shortLabel: 'Devlog',
      pageCount: D.posts.length,
      pages: D.posts.map(function (p) { return { type: 'post', data: p }; }),
    });
  }

  // Libro: Contact — corto, pero con la misma coreografía completa
  // (decisión ya tomada explícitamente).
  books.push({
    id: 'contact',
    type: 'book',
    title: 'Contact',
    shortLabel: 'Contact',
    pageCount: 1,
    pages: [{
      type: 'contact',
      data: {
        links: (D.links || []).filter(function (l) { return l.showInHeader; }),
        location: (D.cv && D.cv.location) || '',
      },
    }],
  });

  // Objetos de mesa (interacción ligera, NO la coreografía de libro).
  const deskObjects = [
    {
      id: 'cv',
      type: 'cv-folder',
      title: 'CV / Resume',
      action: 'open-or-download',
      data: Object.assign({}, D.cv, {
        name: D.profile && D.profile.name,
        role: D.profile && D.profile.role,
      }),
    },
    {
      id: 'vfx-jobs',
      type: 'console',
      title: 'VFX Jobs',
      action: 'open-console',
      // La consola lee directamente de data/jobs.json cuando se activa;
      // aquí solo marcamos si el objeto debe estar visible, según el
      // mismo flag que ya controla la visibilidad pública en Classic.
      visible: !!D.vfxJobsPublic,
    },
  ];

  return { books: books, deskObjects: deskObjects };
}

if (typeof module !== 'undefined') module.exports = { deriveSectionsModel: deriveSectionsModel };
