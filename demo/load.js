const request = require('xhr-request');
const noop = function () {};

module.exports = function (src, cb) {
  cb = cb || noop;
  const container = new THREE.Object3D();
  request(src, { json: true }, (err, json) => {
    if (err) return cb(err);
    const geometries = {};
    Object.keys(json.geometries).forEach(k => {
      const buffer = new THREE.BufferGeometry();
      const {
        normal,
        normalIndices,
        uv,
        uvIndices,
        position,
        positionIndices,
        groups
      } = json.geometries[k];

      const positionArray = new Float32Array(positionIndices.length * 3);
      const normalArray = new Float32Array(positionIndices.length * 3);
      const uvArray = new Float32Array(positionIndices.length * 2);

      for (let i = 0; i < positionIndices.length; i++) {
        const positionIndex = positionIndices[i];
        const normalIndex = normalIndices[i];
        const uvIndex = uvIndices[i];
        for (let j = 0; j < 3; j++) {
          positionArray[i * 3 + j] = position[positionIndex * 3 + j];
          normalArray[i * 3 + j] = normal[normalIndex * 3 + j];
          if (j < 3) uvArray[i * 2 + j] = uv[uvIndex * 2 + j];
        }
      }

      buffer.addAttribute('position', new THREE.BufferAttribute(positionArray, 3));
      buffer.addAttribute('normal', new THREE.BufferAttribute(normalArray, 3));
      buffer.addAttribute('uv', new THREE.BufferAttribute(uvArray, 2));
      buffer.name = k;

      groups.forEach(({ start, count, materialIndex }) => {
        buffer.addGroup(start, count, materialIndex);
      });
      geometries[k] = buffer;
    });

    // A more advanced parser would determine which material
    // to use, e.g. MeshStandardMaterial vs MeshLambertMaterial
    const materials = json.materials.map(material => {
      const loader = new THREE.TextureLoader();
      const map = material.mapDiffuse
        ? loader.load(`${material.mapDiffuse}`)
        : undefined;
      if (map) {
        return new THREE.MeshBasicMaterial({
          side: THREE.DoubleSide,
          map: map
        });
      } else {
        return new THREE.MeshBasicMaterial({
          color: 0xd1d1d1
        });
      }
    });

    const meshes = json.instances.map(instance => {
      if (!(instance.id in geometries)) {
        throw new Error(`Could not find geometry ${instance.id} from mesh ${instance.name}`);
      }

      const geometry = geometries[instance.id];
      const material = new THREE.MultiMaterial(materials);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.fromArray(instance.position);
      mesh.scale.fromArray(instance.scale);
      mesh.quaternion.fromArray(instance.quaternion);
      mesh.name = instance.name;
      return mesh;
    });
    meshes.forEach(mesh => container.add(mesh));
    console.log('Geometries', Object.keys(geometries).length);
    console.log('Meshes', meshes.length);

    cb(null, container);
  });
  return container;
};
