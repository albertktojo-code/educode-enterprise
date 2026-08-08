import { Link } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { productCatalog, productRoute } from '../config/productCatalog'
import './productDirectory.css'

export function ProductDirectoryPage() {
  const { user } = useAuth()
  const role = user?.memberships[0]?.role

  return (
    <section className="product-directory">
      <header className="product-directory-hero">
        <span>ECOSSISTEMA EDUCACIONAL INTEGRADO</span>
        <h1>Nove produtos. Uma única jornada.</h1>
        <p>Explore o EduCode por objetivo. Seus dados, permissões e evidências continuam conectados em uma arquitetura única.</p>
      </header>

      <div className="product-directory-grid">
        {productCatalog.map((product) => (
          <article className={`product-card product-${product.code}`} key={product.code}>
            <span className="product-card-icon" aria-hidden="true">{product.icon}</span>
            <div>
              <small>{product.tagline}</small>
              <h2>{product.name}</h2>
              <p>{product.description}</p>
            </div>
            <ul aria-label={`Recursos do ${product.name}`}>
              {product.capabilities.map((capability) => <li key={capability}>{capability}</li>)}
            </ul>
            <Link to={productRoute(product, role)}>Acessar produto <span aria-hidden="true">→</span></Link>
          </article>
        ))}
      </div>
    </section>
  )
}
