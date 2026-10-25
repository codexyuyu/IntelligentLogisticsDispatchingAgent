<template>
  <div class="viewer-wrap">
    <div class="toolbar">
      <el-radio-group v-model="viewMode" size="small" @change="rebuild">
        <el-radio-button label="overview">总览</el-radio-button>
        <el-radio-button label="storage">存储区</el-radio-button>
        <el-radio-button label="rack">货架模型</el-radio-button>
        <el-radio-button label="layer">分层货架</el-radio-button>
      </el-radio-group>
      <span class="legend">
        <i class="picking"></i>分拣区 <i class="storage"></i>存储区 <i class="normal"></i>正常货架 <i class="warning"></i>预警 <i class="selected"></i>叉车路线
      </span>
    </div>
    <div ref="container" class="viewer"></div>
  </div>
</template>

<script setup>
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  twin: { type: Object, default: () => ({}) },
  path: { type: Array, default: () => [] },
  autoPatrol: { type: Boolean, default: true }
})
const emit = defineEmits(['selectShelf'])
const container = ref(null)
const viewMode = ref('overview')

let scene, camera, renderer, controls, raycaster, mouse
let shelfMeshes = []
let forklift, animationId, pathLine, selectedGroup
let routePoints = []
let routeProgress = 0
let routeDistance = 0
let lastTime = 0

const materials = {}

function getMat(name, color, options = {}) {
  if (!materials[name]) {
    materials[name] = new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0.12, ...options })
  }
  return materials[name]
}

function colorOf(shelf) {
  if (shelf.status === 'WARNING') return 0xef4444
  const rate = (shelf.used || 0) / Math.max(shelf.capacity || 1, 1)
  if (rate > 0.82) return 0xf59e0b
  return 0x2563eb
}

function init() {
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0f172a)
  scene.fog = new THREE.Fog(0x0f172a, 26, 58)

  camera = new THREE.PerspectiveCamera(50, container.value.clientWidth / container.value.clientHeight, 0.1, 1000)
  camera.position.set(18, 18, 24)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  container.value.innerHTML = ''
  container.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.target.set(12, 0, 7)
  controls.maxPolarAngle = Math.PI * 0.47
  controls.minDistance = 10
  controls.maxDistance = 48

  raycaster = new THREE.Raycaster()
  mouse = new THREE.Vector2()
  renderer.domElement.addEventListener('click', onClick)
  window.addEventListener('resize', resize)
  rebuild()
  animate()
}

function rebuild() {
  if (!scene) return
  while (scene.children.length) scene.remove(scene.children[0])
  shelfMeshes = []
  selectedGroup = null
  forklift = null
  pathLine = null
  routePoints = []
  routeProgress = 0
  routeDistance = 0

  addLights()
  addWarehouseShell()
  addZones()
  addAisleLines()

  const shelves = props.twin?.shelves || []
  for (const shelf of shelves) {
    if (viewMode.value === 'layer') addLayerShelf(shelf)
    else addRackShelf(shelf)
  }
  addRouteAndForklift()
  focusCamera()
}

function addLights() {
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 1.6))
  const key = new THREE.DirectionalLight(0xffffff, 1.8)
  key.position.set(8, 18, 10)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  key.shadow.camera.left = -20
  key.shadow.camera.right = 30
  key.shadow.camera.top = 24
  key.shadow.camera.bottom = -12
  scene.add(key)

  const fill = new THREE.DirectionalLight(0x93c5fd, 0.62)
  fill.position.set(-12, 8, -8)
  scene.add(fill)
}

function addWarehouseShell() {
  const w = props.twin?.warehouse?.width || 24
  const d = props.twin?.warehouse?.depth || 14
  const floor = new THREE.Mesh(new THREE.BoxGeometry(w, 0.08, d), getMat('floor', 0x334155))
  floor.position.set(w / 2, -0.05, d / 2)
  floor.receiveShadow = true
  scene.add(floor)

  addWall(w / 2, 1.15, -0.08, w, 2.3, 0.12)
  addWall(w / 2, 1.15, d + 0.08, w, 2.3, 0.12)
  addWall(-0.08, 1.15, d / 2, 0.12, 2.3, d)
  addWall(w + 0.08, 1.15, d / 2, 0.12, 2.3, d)

  addTextSprite('入口', props.twin?.warehouse?.startX || 1, 0.68, props.twin?.warehouse?.startY || 1, '#38bdf8')
  addTextSprite('出库口', props.twin?.warehouse?.exitX || 22, 0.68, props.twin?.warehouse?.exitY || 1, '#a78bfa')
  addDockMarker(props.twin?.warehouse?.startX || 1, props.twin?.warehouse?.startY || 1, 0x38bdf8)
  addDockMarker(props.twin?.warehouse?.exitX || 22, props.twin?.warehouse?.exitY || 1, 0xa78bfa)
}

function addWall(x, y, z, sx, sy, sz) {
  const wall = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), getMat('wall', 0x1e293b, { transparent: true, opacity: 0.58 }))
  wall.position.set(x, y, z)
  wall.receiveShadow = true
  scene.add(wall)
}

function addZones() {
  const zones = props.twin?.zones || [
    { code: 'PICKING', name: '分拣区', x: 0, y: 0, width: 6, depth: 14 },
    { code: 'STORAGE', name: '存储区', x: 6, y: 0, width: 18, depth: 14 }
  ]
  for (const zone of zones) {
    const color = zone.code === 'PICKING' ? 0x0ea5e9 : 0x16a34a
    const plane = new THREE.Mesh(
      new THREE.BoxGeometry(zone.width, 0.035, zone.depth),
      new THREE.MeshStandardMaterial({ color, transparent: true, opacity: zone.code === 'PICKING' ? 0.22 : 0.14, roughness: 0.8 })
    )
    plane.position.set(zone.x + zone.width / 2, 0.012, zone.y + zone.depth / 2)
    plane.receiveShadow = true
    scene.add(plane)

    const border = makeDashedRect(zone.x, zone.y, zone.width, zone.depth, color)
    scene.add(border)
    addTextSprite(zone.name + (zone.code === 'PICKING' ? '（预留）' : ''), zone.x + zone.width / 2, 0.42, zone.y + 0.9, zone.code === 'PICKING' ? '#7dd3fc' : '#86efac')
  }
}

function makeDashedRect(x, y, w, d, color) {
  const points = [
    new THREE.Vector3(x, 0.06, y), new THREE.Vector3(x + w, 0.06, y),
    new THREE.Vector3(x + w, 0.06, y), new THREE.Vector3(x + w, 0.06, y + d),
    new THREE.Vector3(x + w, 0.06, y + d), new THREE.Vector3(x, 0.06, y + d),
    new THREE.Vector3(x, 0.06, y + d), new THREE.Vector3(x, 0.06, y)
  ]
  const geom = new THREE.BufferGeometry().setFromPoints(points)
  return new THREE.LineSegments(geom, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.85 }))
}

function addAisleLines() {
  const d = props.twin?.warehouse?.depth || 14
  for (const x of [6, 10, 14, 18, 22]) {
    const geom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(x, 0.075, 1.2), new THREE.Vector3(x, 0.075, d - 1)])
    scene.add(new THREE.Line(geom, new THREE.LineBasicMaterial({ color: 0x64748b, transparent: true, opacity: 0.36 })))
  }
}

function addDockMarker(x, y, color) {
  const marker = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.08, 32), getMat(`dock-${color}`, color))
  marker.position.set(x, 0.08, y)
  marker.castShadow = true
  scene.add(marker)
}

function addRackShelf(shelf) {
  const group = new THREE.Group()
  group.position.set(shelf.x, 0, shelf.y)
  group.userData = shelf

  const rackWidth = viewMode.value === 'rack' ? 1.55 : 1.35
  const rackDepth = 1.62
  const rackHeight = viewMode.value === 'overview' ? 1.9 : 2.35
  const postMat = getMat('rack-post', 0x475569, { metalness: 0.55, roughness: 0.42 })
  const beamMat = getMat('rack-beam', 0xf97316, { metalness: 0.2, roughness: 0.55 })
  const loadMat = new THREE.MeshStandardMaterial({ color: colorOf(shelf), transparent: true, opacity: 0.82, roughness: 0.68 })

  for (const px of [-rackWidth / 2, rackWidth / 2]) {
    for (const pz of [-rackDepth / 2, rackDepth / 2]) {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, rackHeight, 0.08), postMat)
      post.position.set(px, rackHeight / 2, pz)
      post.castShadow = true
      post.userData = shelf
      group.add(post)
      shelfMeshes.push(post)
    }
  }

  const layers = viewMode.value === 'overview' ? 3 : Math.max(3, shelf.layerCount || 4)
  for (let i = 0; i < layers; i++) {
    const y = 0.38 + i * (rackHeight - 0.42) / Math.max(layers - 1, 1)
    const beam = new THREE.Mesh(new THREE.BoxGeometry(rackWidth + 0.18, 0.08, rackDepth + 0.1), beamMat)
    beam.position.set(0, y, 0)
    beam.castShadow = true
    beam.userData = shelf
    group.add(beam)
    shelfMeshes.push(beam)
  }

  const fillRate = Math.min(1, (shelf.used || 0) / Math.max(shelf.capacity || 1, 1))
  const boxRows = Math.max(1, Math.round(fillRate * 4))
  for (let i = 0; i < boxRows; i++) {
    const cargo = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.28, 0.46), loadMat)
    cargo.position.set(-0.42 + (i % 3) * 0.42, 0.58 + Math.floor(i / 3) * 0.34, i % 2 ? 0.32 : -0.28)
    cargo.castShadow = true
    cargo.userData = shelf
    group.add(cargo)
    shelfMeshes.push(cargo)
  }

  group.traverse(obj => { if (obj.isMesh) obj.userData = shelf })
  scene.add(group)
  addTextSprite(shelf.code, shelf.x, rackHeight + 0.34, shelf.y, shelf.status === 'WARNING' ? '#fecaca' : '#dbeafe')
}

function addLayerShelf(shelf) {
  const group = new THREE.Group()
  group.position.set(shelf.x, 0, shelf.y)
  group.userData = shelf
  const layerHeight = 0.42
  const rackWidth = 1.45
  const rackDepth = 1.62
  for (let i = 0; i < shelf.layerCount; i++) {
    const base = new THREE.Mesh(new THREE.BoxGeometry(rackWidth, 0.08, rackDepth), getMat('rack-beam', 0xf97316, { metalness: 0.2, roughness: 0.55 }))
    base.position.set(0, 0.28 + i * 0.52, 0)
    base.userData = { ...shelf, layerNo: i + 1 }
    base.castShadow = true
    group.add(base)
    shelfMeshes.push(base)

    const load = new THREE.Mesh(new THREE.BoxGeometry(1.05, layerHeight, 1.15), new THREE.MeshStandardMaterial({ color: colorOf(shelf), transparent: true, opacity: 0.52 + i * 0.08 }))
    load.position.set(0, 0.52 + i * 0.52, 0)
    load.userData = { ...shelf, layerNo: i + 1 }
    load.castShadow = true
    group.add(load)
    shelfMeshes.push(load)
  }
  for (const px of [-rackWidth / 2, rackWidth / 2]) {
    for (const pz of [-rackDepth / 2, rackDepth / 2]) {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.5, 0.08), getMat('rack-post', 0x475569, { metalness: 0.55, roughness: 0.42 }))
      post.position.set(px, 1.25, pz)
      post.userData = shelf
      group.add(post)
      shelfMeshes.push(post)
    }
  }
  scene.add(group)
  addTextSprite(shelf.code + ' 分层', shelf.x, 2.78, shelf.y, '#dbeafe')
}

function addRouteAndForklift() {
  const sourcePath = props.path?.length ? props.path : (props.autoPatrol ? props.twin?.forkliftPatrolPath : [])
  if (!sourcePath || sourcePath.length === 0) return
  routePoints = sourcePath.map(p => new THREE.Vector3(p.x, 0.16, p.y))
  drawRouteTube(routePoints)
  forklift = buildForkliftModel()
  forklift.position.copy(routePoints[0])
  forklift.position.y = 0.22
  scene.add(forklift)
  routeDistance = calcPathLength(routePoints)
}

function drawRouteTube(points) {
  if (pathLine) scene.remove(pathLine)
  const group = new THREE.Group()
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i]
    const b = points[i + 1]
    const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5)
    const length = a.distanceTo(b)
    if (length === 0) continue
    const cyl = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, length, 12), getMat('route', 0xfacc15, { emissive: 0x7c2d12, emissiveIntensity: 0.25 }))
    cyl.position.copy(mid)
    cyl.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3().subVectors(b, a).normalize())
    group.add(cyl)
  }
  pathLine = group
  scene.add(pathLine)
}

function buildForkliftModel() {
  const group = new THREE.Group()
  const yellow = getMat('forklift-yellow', 0xfbbf24, { roughness: 0.55, metalness: 0.18 })
  const dark = getMat('forklift-dark', 0x111827, { roughness: 0.75 })
  const metal = getMat('forklift-metal', 0x64748b, { roughness: 0.38, metalness: 0.6 })

  addBox(group, 0, 0.28, 0, 0.76, 0.34, 0.62, yellow)
  addBox(group, -0.16, 0.68, -0.02, 0.42, 0.46, 0.5, yellow)
  addBox(group, 0.28, 0.72, -0.02, 0.08, 0.86, 0.72, metal)
  addBox(group, 0.56, 0.2, -0.18, 0.78, 0.06, 0.06, metal)
  addBox(group, 0.56, 0.2, 0.18, 0.78, 0.06, 0.06, metal)
  addBox(group, 0.44, 0.62, 0, 0.06, 0.92, 0.06, metal)
  for (const wx of [-0.28, 0.28]) {
    for (const wz of [-0.34, 0.34]) {
      const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 0.1, 20), dark)
      wheel.rotation.z = Math.PI / 2
      wheel.position.set(wx, 0.15, wz)
      wheel.castShadow = true
      group.add(wheel)
    }
  }
  group.scale.set(0.9, 0.9, 0.9)
  return group
}

function addBox(parent, x, y, z, sx, sy, sz, mat) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), mat)
  mesh.position.set(x, y, z)
  mesh.castShadow = true
  mesh.receiveShadow = true
  parent.add(mesh)
}

function calcPathLength(points) {
  return points.slice(1).reduce((sum, p, i) => sum + p.distanceTo(points[i]), 0)
}

function updateForklift(delta) {
  if (!forklift || routePoints.length < 2 || routeDistance <= 0) return
  routeProgress = (routeProgress + delta * 2.15) % routeDistance
  let traveled = 0
  for (let i = 0; i < routePoints.length - 1; i++) {
    const a = routePoints[i]
    const b = routePoints[i + 1]
    const seg = a.distanceTo(b)
    if (traveled + seg >= routeProgress) {
      const t = seg === 0 ? 0 : (routeProgress - traveled) / seg
      forklift.position.lerpVectors(a, b, t)
      forklift.position.y = 0.22
      const dir = new THREE.Vector3().subVectors(b, a)
      if (dir.lengthSq() > 0.0001) forklift.rotation.y = Math.atan2(dir.x, dir.z)
      return
    }
    traveled += seg
  }
}

function addTextSprite(text, x, y, z, color = '#ffffff') {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 128
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = 'rgba(15,23,42,0.76)'
  roundRect(ctx, 10, 16, 492, 88, 22)
  ctx.fill()
  ctx.fillStyle = color
  ctx.font = 'bold 44px "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC", Arial, sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(text, 256, 74)
  const texture = new THREE.CanvasTexture(canvas)
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true }))
  sprite.position.set(x, y, z)
  sprite.scale.set(2.2, 0.55, 1)
  scene.add(sprite)
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function onClick(event) {
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)
  const hits = raycaster.intersectObjects(shelfMeshes, true)
  if (hits.length > 0) {
    const shelf = hits[0].object.userData
    emit('selectShelf', shelf)
    highlightShelf(shelf.id)
  }
}

function highlightShelf(shelfId) {
  if (selectedGroup) selectedGroup.traverse(obj => { if (obj.isMesh) obj.material.emissiveIntensity = obj.userData?.status === 'WARNING' ? 0.1 : 0 })
  const object = shelfMeshes.find(mesh => mesh.userData?.id === shelfId)
  selectedGroup = object?.parent || null
  if (selectedGroup) selectedGroup.traverse(obj => {
    if (obj.isMesh && obj.material?.emissive) {
      obj.material.emissive = new THREE.Color(0xfacc15)
      obj.material.emissiveIntensity = 0.25
    }
  })
}

function focusCamera() {
  if (!camera || !controls) return
  const w = props.twin?.warehouse?.width || 24
  const d = props.twin?.warehouse?.depth || 14
  if (viewMode.value === 'storage') {
    camera.position.set(19, 14, 20)
    controls.target.set(15, 0, d / 2)
  } else {
    camera.position.set(18, 18, 24)
    controls.target.set(w / 2, 0, d / 2)
  }
  controls.update()
}

function resize() {
  if (!container.value || !renderer) return
  camera.aspect = container.value.clientWidth / container.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.value.clientWidth, container.value.clientHeight)
}

function animate(time = 0) {
  animationId = requestAnimationFrame(animate)
  const delta = lastTime ? Math.min((time - lastTime) / 1000, 0.05) : 0
  lastTime = time
  updateForklift(delta)
  controls?.update()
  renderer.render(scene, camera)
}

onMounted(init)
onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', resize)
  renderer?.domElement?.removeEventListener('click', onClick)
  controls?.dispose()
  renderer?.dispose()
})
watch(() => props.twin, rebuild, { deep: true })
watch(() => props.path, rebuild, { deep: true })
</script>

<style scoped>
.viewer-wrap { background: #0f172a; border-radius: 16px; padding: 12px; box-shadow: inset 0 0 0 1px rgba(148,163,184,.14); }
.viewer { height: 560px; width: 100%; border-radius: 14px; overflow: hidden; }
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; color: #cbd5e1; gap: 12px; }
.legend { font-size: 12px; white-space: nowrap; }
.legend i { display: inline-block; width: 10px; height: 10px; margin: 0 4px 0 12px; border-radius: 2px; }
.picking { background: #0ea5e9; }
.storage { background: #16a34a; }
.normal { background: #2563eb; }
.warning { background: #ef4444; }
.selected { background: #facc15; }
@media (max-width: 1100px) {
  .toolbar { align-items: flex-start; flex-direction: column; }
  .legend { white-space: normal; }
}
</style>
