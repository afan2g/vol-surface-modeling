import React from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Points, Point } from "@react-three/drei";
function SurfaceSVI() {
  const points = new Float32Array([
    0, 0, 0, 
    1, 0, 0, 
    0, 1, 0, 
    0, 0, 1, 
    1, 1, 0, 
    1, 0, 1, 
    0, 1, 1, 
    1, 1, 1, 
    4, 5, 6, 
    7, 8, 9,
  ]);

  return (
    <div
      className="surface-svi"
      style={{
        borderWidth: "1px",
        borderStyle: "solid",
        borderColor: "black",
        width: "100%",
        height: "1000px",
      }}
    >
      <Canvas>
        <axesHelper args={[100]} />
        <gridHelper args={[10, 10]} position={[5, 0, 5]} />
        <gridHelper
          args={[10, 10]}
          rotation={[Math.PI / 2, 0, 0]}
          position={[5, 5, 0]}
        />
        <gridHelper
          args={[10, 10]}
          rotation={[0, 0, Math.PI / 2]}
          position={[0, 5, 5]}
        />
        <Points positions={points} size={0.1} color={"#00ff00"}>
          <pointsMaterial vertexColors={true} size={1} />
        </Points>
        <OrbitControls />
      </Canvas>
    </div>
  );
}

export default SurfaceSVI;
