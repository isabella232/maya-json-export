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
  antialias: true,
  position: [ 0, 100, 0 ]
});

renderer.setClearColor('#24bdf4', 1);

const city = loadModel('demo/city.jsm', (err) => {
  if (err) return window.alert(err.message);
});
scene.add(city);

city.position.x = 6;
city.position.z = 10;
city.scale.multiplyScalar(0.01);

// Render loop
createLoop(function () {
  updateProjectionMatrix();

  // Render instanced meshes
  renderer.render(scene, camera);
}).start();
