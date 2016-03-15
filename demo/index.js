global.THREE = require('three');
const createApp = require('./app');
const createLoop = require('raf-loop');
const loadModel = require('./load');

// create our app, passing GL context and canvas along!
const {
  renderer,
  camera,
  scene,
  updateProjectionMatrix
} = createApp({
  antialias: true
});

renderer.setClearColor('#24bdf4', 1);

const city = loadModel('demo/House.jsm', (err) => {
  if (err) return window.alert(err.message);
});
scene.add(city);

city.position.z = 6;
city.rotation.y = -Math.PI / 2;
city.scale.multiplyScalar(0.15);

// Render loop
createLoop(function () {
  updateProjectionMatrix();

  // Render instanced meshes
  renderer.render(scene, camera);
}).start();
