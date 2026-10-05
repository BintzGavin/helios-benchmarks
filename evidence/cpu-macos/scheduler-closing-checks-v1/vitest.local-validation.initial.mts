import { defineWorkersConfig } from '/private/tmp/helios-scheduler-merge-20261001/node_modules/@cloudflare/vitest-pool-workers/dist/config/index.cjs';
export default defineWorkersConfig({
  root: '/private/tmp/helios-scheduler-merge-20261001',
  envDir: false,
  test: {
    include: ['test/media-streaming.test.ts', 'test/sandbox-audio.test.ts', 'test/render-readiness.test.ts'],
    poolOptions: {
      workers: {
        remoteBindings: false,
        miniflare: {
          compatibilityDate: '2026-02-10',
          compatibilityFlags: ['nodejs_compat'],
          r2Buckets: ['MEMORY'],
        },
      },
    },
  },
});
