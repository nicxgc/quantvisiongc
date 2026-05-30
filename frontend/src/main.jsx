import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntApp } from 'antd'
import esES from 'antd/locale/es_ES'
import App from './App.jsx'
import './index.css'

// Se envuelve la app con el componente App de Ant Design (AntApp) además
// del ConfigProvider. Esto habilita los hooks message/modal/notification
// con acceso al tema, que se usarán en las confirmaciones y avisos a
// partir de la contratación (T5.7).
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={esES}
      theme={{
        token: {
          colorPrimary: '#185FA5',
          borderRadius: 6,
        },
      }}
    >
      <AntApp>
        <App />
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
)
