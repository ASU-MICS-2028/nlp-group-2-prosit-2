// Adds readable checks like expect(element).toBeInTheDocument()
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Remove what each test drew on the page, so tests cannot affect each other
afterEach(cleanup)
