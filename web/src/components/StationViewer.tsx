import { Canvas, useLoader } from '@react-three/fiber';
import { Center, OrbitControls } from '@react-three/drei';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Box3, Mesh, MeshStandardMaterial, Vector3 } from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import type { Group } from 'three';
import type { StationState } from '../types';

const DEFAULT_CAMERA: [number, number, number] = [0, 2.2, 9];

function StationModel({
  position,
  roll,
  pitch,
  yaw,
  active,
  modelPath,
}: {
  position: [number, number, number];
  roll: number;
  pitch: number;
  yaw: number;
  active: boolean;
  modelPath: string;
}) {
  const obj = useLoader(OBJLoader, modelPath) as Group;
  const clone = useMemo(() => {
    const next = obj.clone(true);
    const box = new Box3().setFromObject(next);
    const size = box.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    next.scale.setScalar(1.8 / maxDim);
    return next;
  }, [obj]);

  useEffect(() => {
    const color = active ? '#4a7c59' : '#888888';
    clone.traverse((child) => {
      if (child instanceof Mesh) {
        child.material = new MeshStandardMaterial({ color, metalness: 0.2, roughness: 0.6 });
      }
    });
  }, [clone, active]);

  const rotation = useMemo(
    () => [(-pitch * Math.PI) / 180, ((yaw + 90) * Math.PI) / 180, (-roll * Math.PI) / 180] as [
      number,
      number,
      number,
    ],
    [roll, pitch, yaw],
  );

  return (
    <group position={position} rotation={rotation}>
      <Center>
        <primitive object={clone} />
      </Center>
    </group>
  );
}

export function StationViewer({
  stations,
  visibleCount,
  modelIndex,
}: {
  stations: StationState[];
  visibleCount: number;
  modelIndex: number;
}) {
  const modelPath = modelIndex === 0 ? '/models/frdm.obj' : '/models/plane.obj';
  const spacing = 2.8;
  const offset = ((visibleCount - 1) * spacing) / 2;
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const [resetToken, setResetToken] = useState(0);

  const resetView = () => {
    const controls = controlsRef.current;
    if (!controls) return;
    controls.target.set(0, 0, 0);
    controls.object.position.set(...DEFAULT_CAMERA);
    controls.update();
    setResetToken((n) => n + 1);
  };

  return (
    <div className="viewer-panel">
      <div className="viewer-toolbar">
        <button type="button" className="btn-secondary" onClick={resetView}>
          Reset view
        </button>
      </div>
      <Canvas key={resetToken} camera={{ position: DEFAULT_CAMERA, fov: 45 }}>
        <color attach="background" args={['#e8ecef']} />
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 8, 5]} intensity={1.1} />
        <axesHelper args={[1.6]} />
        <gridHelper args={[12, 12, '#c5ced6', '#dde3e8']} />
        <Suspense fallback={null}>
          {stations.slice(0, visibleCount).map((station, i) => (
            <StationModel
              key={`${modelPath}-${i}`}
              position={[i * spacing - offset, 0, 0]}
              roll={station.roll}
              pitch={station.pitch}
              yaw={station.yaw}
              active={station.active}
              modelPath={modelPath}
            />
          ))}
        </Suspense>
        <OrbitControls ref={controlsRef} makeDefault />
      </Canvas>
    </div>
  );
}
