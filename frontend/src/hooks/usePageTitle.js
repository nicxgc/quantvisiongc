import { useEffect } from 'react'

const APP_NAME = 'QuantVisionGC'

// Actualiza el title del documento (la pestaña del navegador) cuando una vista
// se monta o su título cambia. Devuelve el título anterior al desmontar para que
// no quede colgado un título de una página que ya no se muestra.
export default function usePageTitle(titulo) {
  useEffect(() => {
    const anterior = document.title
    document.title = titulo ? `${titulo} · ${APP_NAME}` : APP_NAME
    return () => { document.title = anterior }
  }, [titulo])
}
