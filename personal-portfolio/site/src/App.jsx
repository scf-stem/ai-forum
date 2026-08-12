import { useEffect, useState } from 'react'
import Nav from './components/Nav'
import Hero from './components/Hero'
import WorksGrid from './components/WorksGrid'
import About from './components/About'
import Footer from './components/Footer'

export default function App() {
  // Page-load curtain: keep mounted 1 tick so animation plays, then remove node
  const [curtainOpen, setCurtainOpen] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setCurtainOpen(false), 1100)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="relative min-h-screen">
      {/* Atmosphere (fixed, z-0) */}
      <div className="atmosphere" aria-hidden>
        <div className="atmosphere__mesh" />
        <div className="atmosphere__grain" />
      </div>

      {/* Content (relative, sits above atmosphere) */}
      <div className="relative z-10">
        <Nav />
        <main>
          <Hero />
          <WorksGrid />
          <About />
        </main>
        <Footer />
      </div>

      {/* Page-load curtain (mounted briefly) */}
      {curtainOpen && (
        <div className="curtain" role="presentation" aria-hidden />
      )}
    </div>
  )
}
