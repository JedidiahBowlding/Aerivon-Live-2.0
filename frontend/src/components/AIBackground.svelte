<script lang="ts">
  import { onMount } from 'svelte';
  import * as THREE from 'three';

  let container: HTMLDivElement;

  onMount(() => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 0.1, 1800);
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    const geometry = new THREE.BufferGeometry();
    const vertices: number[] = [];

    for (let i = 0; i < 8500; i += 1) {
      vertices.push(
        THREE.MathUtils.randFloatSpread(1700),
        THREE.MathUtils.randFloatSpread(900),
        THREE.MathUtils.randFloatSpread(1600)
      );
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

    const material = new THREE.PointsMaterial({
      color: 0x5ec4ff,
      size: 1.6,
      transparent: true,
      opacity: 0.7
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);
    camera.position.z = 520;

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    const clock = new THREE.Clock();
    let raf = 0;

    const animate = () => {
      const t = clock.getElapsedTime();
      points.rotation.y = t * 0.05;
      points.rotation.x = Math.sin(t * 0.25) * 0.12;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };

    window.addEventListener('resize', onResize);
    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  });
</script>

<div bind:this={container} class="pointer-events-none fixed inset-0 z-0 opacity-60"></div>
