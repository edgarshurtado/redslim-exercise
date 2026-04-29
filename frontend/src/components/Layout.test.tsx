import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Layout from './Layout'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="*" element={<div />} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

test('explore link shows active indicator at /explore', () => {
  renderAt('/explore')
  const exploreLink = screen.getByRole('link', { name: /explore/i })
  expect(exploreLink).toHaveClass('border-b-2', 'border-nav-accent', 'pb-0.5')
})

test('explore link has no active indicator when not at /explore', () => {
  renderAt('/')
  const exploreLink = screen.getByRole('link', { name: /explore/i })
  expect(exploreLink).not.toHaveClass('border-b-2')
})

test('evolution link shows active indicator at /evolution', () => {
  renderAt('/evolution')
  const link = screen.getByRole('link', { name: /evolution/i })
  expect(link).toHaveClass('border-b-2', 'border-nav-accent', 'pb-0.5')
})

test('evolution link has no active indicator when not at /evolution', () => {
  renderAt('/')
  const link = screen.getByRole('link', { name: /evolution/i })
  expect(link).not.toHaveClass('border-b-2')
})
