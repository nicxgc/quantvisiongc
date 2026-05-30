import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import usePageTitle from '../hooks/usePageTitle'

export default function NotFound() {
  const navigate = useNavigate()
  usePageTitle('Página no encontrada')

  return (
    <Result
      status="404"
      title="404"
      subTitle="Esta página no existe o no tienes acceso a ella."
      extra={
        <Button type="primary" onClick={() => navigate('/dashboard')}>
          Volver al dashboard
        </Button>
      }
    />
  )
}
