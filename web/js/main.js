import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const CATEGORY_LABELS = {
  laringe: "Laringe e pregas vocais",
  cavidade_oral_lingua: "Cavidade oral e língua",
  faringe: "Faringe",
  atm: "ATM (temporomandibular)",
  nervo_I_olfatorio: "N. craniano I — Olfatório",
  nervo_II_optico: "N. craniano II — Óptico",
  nervo_III_oculomotor: "N. craniano III — Oculomotor",
  nervo_IV_troclear: "N. craniano IV — Troclear",
  nervo_V_trigemeo: "N. craniano V — Trigêmeo",
  nervo_VII_facial: "N. craniano VII — Facial",
  nervo_IX_glossofaringeo: "N. craniano IX — Glossofaríngeo",
  nervo_X_vago: "N. craniano X — Vago",
  nervo_XI_acessorio: "N. craniano XI — Acessório",
  nervo_XII_hipoglosso: "N. craniano XII — Hipoglosso",
  cerebro: "Cérebro",
  cranio_ossos: "Ossos do crânio",
  musculos_pescoco: "Músculos do pescoço",
  regioes_superficie: "Regiões de superfície (pele)",
  orelha_nariz_cartilagem: "Cartilagens da orelha e nariz",
  marcos_osseos: "Marcos ósseos (forames, canais, suturas)",
};

const MARKER_CATEGORY = "marcos_osseos";

const DEFAULT_CHECKED = new Set(["laringe"]);

const state = {
  manifest: null,
  categories: {}, // key -> { root, loaded, loading, objects: Map(name->mesh), listEl, checkboxEl, headerLoadingEl }
  selected: null, // mesh
  framedOnce: false,
  photos: null, // config data/photos.json: normalized_key -> nome do arquivo em data/photos/
};

const holder = document.getElementById("canvas-holder");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x12161c);

const camera = new THREE.PerspectiveCamera(45, holder.clientWidth / holder.clientHeight, 0.01, 100);
camera.position.set(0.3, 0.2, 0.3);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(holder.clientWidth, holder.clientHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
holder.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.AmbientLight(0xffffff, 0.65));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.3);
keyLight.position.set(1, 2, 1.5);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0xffffff, 0.55);
fillLight.position.set(-1.5, -0.3, -1);
scene.add(fillLight);
const rimLight = new THREE.DirectionalLight(0xffffff, 0.4);
rimLight.position.set(0, -1.5, -1.2);
scene.add(rimLight);

// --- coloracao por tipo de tecido (heuristica por nome, ja que os materiais
// originais do Z-Anatomy usam um shader customizado que nao exporta corretamente
// para glTF padrao) ---
const TISSUE_RULES = [
  [/nerve|nervo|nucleus|ganglion/i, 0xf2cf4a],
  [/muscle|musculo/i, 0xa3384a],
  [/cartilage|cartilagem/i, 0xcdd8e6],
  [/ligament|membrane/i, 0xe9e2cf],
  [/joint|capsule|disc/i, 0x8fb3d9],
  [/gland/i, 0xd9a066],
  [/tonsil|lymph/i, 0xd98fae],
  [/bone|canal|fossa|condyle|plate|process|tubercle/i, 0xe8e2d0],
  [/artery/i, 0xc0392b],
  [/vein/i, 0x3a6ea5],
];
const materialCache = new Map();
function materialForName(name) {
  let color = 0xd08c8c; // tecido mole generico (mucosa, orgao)
  for (const [re, c] of TISSUE_RULES) {
    if (re.test(name)) { color = c; break; }
  }
  if (materialCache.has(color)) return materialCache.get(color);
  const mat = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.55,
    metalness: 0.05,
    side: THREE.DoubleSide,
  });
  materialCache.set(color, mat);
  return mat;
}

// marcos osseos (forames/canais/suturas) sao esferas sinteticas - cor de "pino"
// bem distinta pra ficarem faceis de achar sobre o osso
const MARKER_MATERIAL = new THREE.MeshStandardMaterial({
  color: 0xff6b3d,
  emissive: 0x7a2c10,
  emissiveIntensity: 0.5,
  roughness: 0.4,
  metalness: 0.1,
});

function materialForMesh(mesh) {
  if (mesh.userData.category === MARKER_CATEGORY) return MARKER_MATERIAL;
  return materialForName(mesh.name);
}

// material unico usado para destacar a peca selecionada (troca o material da
// malha em vez de desenhar uma caixa ao redor dela)
const HIGHLIGHT_MATERIAL = new THREE.MeshStandardMaterial({
  color: 0x4fb0ff,
  emissive: 0x1c5f9e,
  emissiveIntensity: 0.7,
  roughness: 0.35,
  metalness: 0.1,
  side: THREE.DoubleSide,
});

window.addEventListener("resize", () => {
  camera.aspect = holder.clientWidth / holder.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(holder.clientWidth, holder.clientHeight);
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

const SUFFIX_RE = /^(.*)\.([a-zA-Z0-9]{1,3})$/;
function baseName(n) {
  const m = SUFFIX_RE.exec(n.trim());
  if (m && m[2].length <= 3) return m[1].trim();
  return n.trim();
}

function normalizeKey(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
}

function lookupDescription(nodeName) {
  if (!state.manifest) return { text: "", fallback: false };
  const key = normalizeKey(baseName(nodeName));
  const pt = state.manifest.descriptions_pt && state.manifest.descriptions_pt[key];
  if (pt) return { text: pt, fallback: false };
  const fb = state.manifest.descriptions_fallback && state.manifest.descriptions_fallback[key];
  if (fb) return { text: fb, fallback: true };
  const en = state.manifest.descriptions_en && state.manifest.descriptions_en[key];
  if (en) return { text: en, fallback: false };
  return { text: "", fallback: false };
}

function photoForName(nodeName) {
  if (!state.photos) return null;
  const key = normalizeKey(baseName(nodeName));
  return state.photos[key] || null;
}

function displayName(nodeName) {
  if (!state.manifest) return baseName(nodeName);
  const key = normalizeKey(baseName(nodeName));
  return (state.manifest.names_pt && state.manifest.names_pt[key]) || baseName(nodeName);
}

const loader = new GLTFLoader();

function frameObject(object3d) {
  const box = new THREE.Box3().setFromObject(object3d);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(center);
  const dir = new THREE.Vector3(0.5, 0.35, 0.8).normalize();
  camera.position.copy(center.clone().add(dir.multiplyScalar(size * 0.9 || 0.3)));
  camera.near = Math.max(size / 1000, 0.001);
  camera.far = size * 50;
  camera.updateProjectionMatrix();
  controls.update();
}

async function loadCategory(catKey) {
  const cat = state.categories[catKey];
  if (cat.loaded || cat.loading) return;
  cat.loading = true;
  cat.headerLoadingEl.textContent = "carregando…";
  const meta = state.manifest.categories[catKey];
  try {
    const gltf = await loader.loadAsync(`../data/glb/${meta.file}`);
    const root = gltf.scene;
    root.name = `category:${catKey}`;
    root.traverse((child) => {
      if (child.isMesh) {
        // o exportador glTF do Blender sanitiza nomes de nos (troca espaco por "_",
        // remove "."), entao usamos o nome original preservado via extras/orig_name
        const origName = child.userData && child.userData.orig_name ? child.userData.orig_name : child.name;
        child.name = origName;
        cat.objects.set(child.name, child);
        child.userData.category = catKey;
        child.material = materialForMesh(child);
      }
    });
    scene.add(root);
    cat.root = root;
    cat.loaded = true;
    cat.headerLoadingEl.textContent = "";
    if (!state.framedOnce) {
      frameObject(root);
      state.framedOnce = true;
    }
  } catch (err) {
    console.error(`Falha ao carregar ${catKey}`, err);
    cat.headerLoadingEl.textContent = "erro";
  } finally {
    cat.loading = false;
  }
  maybeHideLoadingOverlay();
}

function setCategoryVisible(catKey, visible) {
  const cat = state.categories[catKey];
  if (cat.root) cat.root.visible = visible;
}

function clearSelection() {
  if (state.selected) {
    state.selected.material = materialForMesh(state.selected);
  }
  state.selected = null;
  document.querySelectorAll(".struct-item.active").forEach((el) => el.classList.remove("active"));
}

function selectMesh(mesh) {
  clearSelection();
  state.selected = mesh;
  mesh.material = HIGHLIGHT_MATERIAL;

  const catKey = mesh.userData.category;
  const listItem = document.querySelector(`.struct-item[data-cat="${catKey}"][data-name="${CSS.escape(mesh.name)}"]`);
  if (listItem) {
    listItem.classList.add("active");
    const list = listItem.closest(".struct-list");
    if (list) list.classList.add("open");
    listItem.scrollIntoView({ block: "center" });
  }

  showInfoPanel(mesh.name, catKey);
}

function showInfoPanel(nodeName, catKey) {
  const panel = document.getElementById("info-panel");
  const title = document.getElementById("info-title");
  const englishName = document.getElementById("info-english");
  const catLabel = document.getElementById("info-cat");
  const desc = document.getElementById("info-desc");
  const photoBox = document.getElementById("info-photo");
  const searchBtn = document.getElementById("info-search-btn");

  const pt = displayName(nodeName);
  const en = baseName(nodeName);
  title.textContent = pt;
  englishName.textContent = pt.toLowerCase() !== en.toLowerCase() ? `(en: ${en})` : "";
  catLabel.textContent = CATEGORY_LABELS[catKey] || catKey;

  const { text, fallback } = lookupDescription(nodeName);
  desc.innerHTML = "";
  if (text) {
    desc.classList.remove("empty");
    const main = document.createElement("span");
    main.textContent = text;
    desc.appendChild(main);
    if (fallback) {
      const note = document.createElement("span");
      note.className = "generic-note";
      note.textContent = "Descrição baseada em conhecimento anatômico geral (esta estrutura ainda não tem um artigo de referência específico na base de dados).";
      desc.appendChild(note);
    }
  } else {
    desc.textContent = "Sem descrição disponível para esta estrutura ainda.";
    desc.classList.add("empty");
  }

  photoBox.hidden = false;
  searchBtn.hidden = false;
  const photoFile = photoForName(nodeName);
  photoBox.innerHTML = "";
  if (photoFile) {
    const img = document.createElement("img");
    img.src = `../data/photos/${photoFile}`;
    img.alt = pt;
    img.onerror = () => {
      photoBox.innerHTML = `<div class="photo-placeholder"><div class="icon">📷</div><div>foto em breve</div></div>`;
    };
    photoBox.appendChild(img);
  } else {
    photoBox.innerHTML = `<div class="photo-placeholder"><div class="icon">📷</div><div>foto em breve</div></div>`;
  }

  searchBtn.textContent = `🔎 Pesquisar sobre ${pt}`;
  searchBtn.onclick = () => searchStructure(nodeName);

  panel.classList.add("open");
}

function closeInfoPanel() {
  document.getElementById("info-panel").classList.remove("open");
  document.getElementById("info-photo").hidden = true;
  document.getElementById("info-search-btn").hidden = true;
  clearSelection();
}

document.getElementById("info-close").addEventListener("click", closeInfoPanel);

// --- raycasting / click to select ---
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

function meshAtEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);

  const pickables = [];
  for (const cat of Object.values(state.categories)) {
    if (cat.root && cat.root.visible) {
      cat.root.traverse((child) => {
        if (child.isMesh && child.visible) pickables.push(child);
      });
    }
  }
  const hits = raycaster.intersectObjects(pickables, false);
  return hits.length > 0 ? hits[0].object : null;
}

renderer.domElement.addEventListener("click", (event) => {
  const mesh = meshAtEvent(event);
  if (mesh) selectMesh(mesh);
});

// --- menu de contexto (botao direito) ---
const ctxMenu = document.getElementById("ctx-menu");

function hideContextMenu() {
  ctxMenu.hidden = true;
}

function showContextMenu(x, y, mesh) {
  const pt = displayName(mesh.name);
  ctxMenu.innerHTML = "";

  const makeItem = (label, onClick) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ctx-item";
    btn.textContent = label;
    btn.addEventListener("click", () => {
      onClick();
      hideContextMenu();
    });
    ctxMenu.appendChild(btn);
  };

  const nameEl = document.createElement("div");
  nameEl.className = "ctx-header";
  nameEl.textContent = pt;
  ctxMenu.appendChild(nameEl);

  makeItem("👁 Selecionar", () => selectMesh(mesh));
  makeItem("🚫 Ocultar", () => hideMesh(mesh));
  makeItem("🎯 Isolar", () => {
    selectMesh(mesh);
    isolateMesh(mesh);
  });
  makeItem("↺ Mostrar tudo", showAllMeshes);
  makeItem("🔎 Pesquisar sobre esta estrutura", () => searchStructure(mesh.name));

  ctxMenu.hidden = false;
  // mantem o menu dentro da janela
  const menuW = 240;
  const menuH = ctxMenu.children.length * 34 + 12;
  const left = Math.min(x, window.innerWidth - menuW - 8);
  const top = Math.min(y, window.innerHeight - menuH - 8);
  ctxMenu.style.left = `${left}px`;
  ctxMenu.style.top = `${top}px`;
}

renderer.domElement.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  const mesh = meshAtEvent(event);
  if (!mesh) {
    hideContextMenu();
    return;
  }
  selectMesh(mesh);
  showContextMenu(event.clientX, event.clientY, mesh);
});

window.addEventListener("click", (event) => {
  if (!ctxMenu.hidden && !ctxMenu.contains(event.target)) hideContextMenu();
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") hideContextMenu();
});
window.addEventListener("blur", hideContextMenu);

// --- toolbar ---
function syncEyeIcons() {
  document.querySelectorAll(".struct-item").forEach((item) => {
    const catKey = item.dataset.cat;
    const objName = item.dataset.name;
    const cat = state.categories[catKey];
    const mesh = cat && cat.objects.get(objName);
    const eyeBtn = item.querySelector(".struct-eye");
    if (!mesh || !eyeBtn) return;
    eyeBtn.classList.toggle("hidden-eye", !mesh.visible);
    eyeBtn.textContent = mesh.visible ? "👁" : "🚫";
  });
}

function isolateMesh(mesh) {
  const keepBase = baseName(mesh.name).toLowerCase();
  for (const cat of Object.values(state.categories)) {
    if (!cat.root) continue;
    cat.root.traverse((child) => {
      if (child.isMesh) {
        child.visible = baseName(child.name).toLowerCase() === keepBase;
      }
    });
  }
  syncEyeIcons();
}

function showAllMeshes() {
  for (const cat of Object.values(state.categories)) {
    if (!cat.root) continue;
    cat.root.traverse((child) => {
      if (child.isMesh) child.visible = true;
    });
  }
  syncEyeIcons();
}

function hideMesh(mesh) {
  mesh.visible = false;
  syncEyeIcons();
  if (state.selected === mesh) closeInfoPanel();
}

function searchStructure(nodeName) {
  const pt = displayName(nodeName);
  const query = `${pt} anatomia função`;
  const url = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
  window.open(url, "_blank", "noopener");
}

document.getElementById("btn-isolate").addEventListener("click", () => {
  if (!state.selected) return;
  isolateMesh(state.selected);
});

document.getElementById("btn-reset").addEventListener("click", showAllMeshes);

// --- sidebar build ---
function buildSidebar(manifest) {
  const container = document.getElementById("categories");
  for (const [catKey, meta] of Object.entries(manifest.categories)) {
    state.categories[catKey] = {
      root: null,
      loaded: false,
      loading: false,
      objects: new Map(),
    };

    const catDiv = document.createElement("div");
    catDiv.className = "category";

    const header = document.createElement("div");
    header.className = "category-header";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = DEFAULT_CHECKED.has(catKey);

    const title = document.createElement("div");
    title.className = "category-title";
    title.textContent = CATEGORY_LABELS[catKey] || catKey;

    const count = document.createElement("div");
    count.className = "category-count";
    count.textContent = meta.objects.length;

    const loadingEl = document.createElement("div");
    loadingEl.className = "category-loading";
    state.categories[catKey].headerLoadingEl = loadingEl;

    header.appendChild(checkbox);
    header.appendChild(title);
    header.appendChild(count);
    header.appendChild(loadingEl);

    const structList = document.createElement("div");
    structList.className = "struct-list";
    for (const objName of meta.objects) {
      const item = document.createElement("div");
      item.className = "struct-item";
      item.dataset.cat = catKey;
      item.dataset.name = objName;
      item.dataset.en = baseName(objName).toLowerCase();

      const label = document.createElement("span");
      label.className = "struct-label";
      label.textContent = displayName(objName);
      label.title = baseName(objName); // nome em ingles no tooltip, util p/ cruzar com literatura

      const eyeBtn = document.createElement("button");
      eyeBtn.className = "struct-eye";
      eyeBtn.type = "button";
      eyeBtn.title = "Mostrar/ocultar";
      eyeBtn.textContent = "👁";

      label.addEventListener("click", async (e) => {
        e.stopPropagation();
        checkbox.checked = true;
        await loadCategory(catKey);
        setCategoryVisible(catKey, true);
        const mesh = state.categories[catKey].objects.get(objName);
        if (mesh) {
          mesh.visible = true;
          eyeBtn.classList.remove("hidden-eye");
          selectMesh(mesh);
          frameSelected(mesh);
        }
      });

      eyeBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        checkbox.checked = true;
        await loadCategory(catKey);
        setCategoryVisible(catKey, true);
        const mesh = state.categories[catKey].objects.get(objName);
        if (!mesh) return;
        mesh.visible = !mesh.visible;
        eyeBtn.classList.toggle("hidden-eye", !mesh.visible);
        eyeBtn.textContent = mesh.visible ? "👁" : "🚫";
        if (!mesh.visible && state.selected === mesh) {
          closeInfoPanel();
        }
      });

      item.appendChild(label);
      item.appendChild(eyeBtn);
      structList.appendChild(item);
    }
    state.categories[catKey].listEl = structList;

    header.addEventListener("click", () => {
      structList.classList.toggle("open");
    });

    checkbox.addEventListener("click", (e) => e.stopPropagation());
    checkbox.addEventListener("change", async () => {
      if (checkbox.checked) {
        await loadCategory(catKey);
        setCategoryVisible(catKey, true);
      } else {
        setCategoryVisible(catKey, false);
      }
    });

    catDiv.appendChild(header);
    catDiv.appendChild(structList);
    container.appendChild(catDiv);
  }
}

function frameSelected(mesh) {
  const box = new THREE.Box3().setFromObject(mesh);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const size = Math.max(box.getSize(new THREE.Vector3()).length(), 0.02);
  controls.target.copy(center);
  const dir = camera.position.clone().sub(controls.target).normalize();
  camera.position.copy(center.clone().add(dir.multiplyScalar(size * 2.2)));
  camera.near = size / 200;
  camera.far = size * 200;
  camera.updateProjectionMatrix();
  controls.update();
}

// --- search ---
document.getElementById("search").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll(".struct-item").forEach((item) => {
    const match =
      q.length === 0 ||
      item.textContent.toLowerCase().includes(q) ||
      (item.dataset.en && item.dataset.en.includes(q));
    item.style.display = match ? "" : "none";
  });
  if (q.length > 0) {
    document.querySelectorAll(".struct-list").forEach((list) => {
      const anyVisible = Array.from(list.children).some((c) => c.style.display !== "none");
      list.classList.toggle("open", anyVisible);
    });
  }
});

function maybeHideLoadingOverlay() {
  document.getElementById("loading-overlay").style.display = "none";
}

window.__debug = { state, scene, camera, renderer, THREE };

async function loadPhotosConfig() {
  try {
    const res = await fetch("../data/photos.json", { cache: "no-store" });
    const raw = await res.json();
    const normalized = {};
    for (const [k, v] of Object.entries(raw)) {
      if (k.startsWith("_")) continue; // chaves de documentacao (_readme, _exemplo)
      normalized[normalizeKey(k)] = v;
    }
    state.photos = normalized;
  } catch (err) {
    console.warn("Nao foi possivel carregar data/photos.json", err);
    state.photos = {};
  }
}

async function init() {
  const res = await fetch("../data/glb/manifest.json", { cache: "no-store" });
  state.manifest = await res.json();
  await loadPhotosConfig();
  buildSidebar(state.manifest);

  const defaultLoads = Object.keys(state.categories).filter((k) => DEFAULT_CHECKED.has(k));
  if (defaultLoads.length === 0) {
    maybeHideLoadingOverlay();
  } else {
    for (const catKey of defaultLoads) {
      await loadCategory(catKey);
      setCategoryVisible(catKey, true);
    }
    maybeHideLoadingOverlay();
  }
}

init().catch((err) => {
  console.error(err);
  document.getElementById("loading-text").textContent = "Erro ao carregar. Veja o console.";
});
