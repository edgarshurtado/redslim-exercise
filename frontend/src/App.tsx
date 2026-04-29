import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Explore from './pages/Explore'
import Dominance from './pages/Dominance'
import Evolution from './pages/Evolution'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/dominance" element={<Dominance />} />
        <Route path="/evolution" element={<Evolution />} />
      </Route>
    </Routes>
  )
}

export default App
