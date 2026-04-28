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

test('home link has Tailwind classes and no inline style', () => {
  renderAt('/')
  const homeLink = screen.getByRole('link', { name: /edgar's readslim exercise/i })
  expect(homeLink).toHaveClass('text-white', 'font-bold', 'text-base', 'no-underline')
  expect(homeLink).not.toHaveAttribute('style')
})

test('explore link has Tailwind classes and no inline style', () => {
  renderAt('/')
  const exploreLink = screen.getByRole('link', { name: /explore/i })
  expect(exploreLink).toHaveClass('text-nav-accent', 'no-underline', 'ml-4', 'text-sm')
  expect(exploreLink).not.toHaveAttribute('style')
})

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
