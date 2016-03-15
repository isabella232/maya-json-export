/*
  A generic orbiter ThreeJS app.
 */
const createControls = require('orbit-controls');

module.exports = createApp;
function createApp (opt = {}) {
  // Scale for retina
  const dpr = window.devicePixelRatio;

  // Our WebGL renderer with alpha and device-scaled
  const renderer = new THREE.WebGLRenderer(opt);
  renderer.setPixelRatio(dpr);

  // Show the <canvas> on screen
  const canvas = renderer.domElement;
  document.body.appendChild(canvas);

  // 3D camera looking at [ 0, 0, 0 ]
  const target = new THREE.Vector3();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  camera.position.copy(new THREE.Vector3().fromArray(opt.position || [ 0, 0, 0]));
  camera.lookAt(target);

  // 3D scene
  const scene = new THREE.Scene();

  // 3D orbit controller
  const controls = createControls({
    distance: 15,
    distanceBounds: [0, Infinity],
    phi: 1,
    theta: 1
  });

  // Update frame size
  window.addEventListener('resize', resize);
  resize();

  // Create a requestAnimationFrame loop
  return {
    renderer,
    camera,
    controls,
    scene,
    updateProjectionMatrix
  };

  function updateProjectionMatrix () {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const aspect = width / height;

    // update controls
    controls.update();
    camera.position.fromArray(controls.position);
    camera.up.fromArray(controls.up);
    camera.lookAt(target.fromArray(controls.direction));
    renderer.render(scene, camera);

    // Update camera matrices
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
  }

  function resize () {
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
}
