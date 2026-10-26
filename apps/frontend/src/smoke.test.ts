// Workspace smoke test: `vitest run` exits non-zero when it collects zero test
// files, which used to fail CI before any real frontend test existed. This
// keeps the runner honest without pretending coverage exists.
import { describe, expect, it } from 'vitest'

describe('frontend workspace smoke', () => {
  it('runs at least one vitest test', () => {
    expect([1, 2, 3].filter((n) => n > 1)).toEqual([2, 3])
  })
})
