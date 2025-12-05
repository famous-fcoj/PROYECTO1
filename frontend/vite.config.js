import { defineConfig } from 'vite'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

// Esto es necesario para obtener la ruta actual en módulos modernos
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

export default defineConfig({
  // Le decimos a Vite que la raíz del proyecto es la carpeta actual
  root: '.', 
  
  build: {
    rollupOptions: {
      input: {
        // Aquí declaramos tus 3 páginas como puntos de entrada independientes
        main: resolve(__dirname, 'index.html'),
        listado: resolve(__dirname, 'ot_listado.html'),
        graficos: resolve(__dirname, 'ot_graficos.html'),
      },
    },
  },
  
  server: {
    port: 3000,
    host: '0.0.0.0', // Permite acceso desde la red local si es necesario
    cors: true,
    // Esto es clave: si pides un archivo html, que no te redirija al index
    strictPort: true,
  }
})