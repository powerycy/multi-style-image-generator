import test from 'node:test'
import assert from 'node:assert/strict'
import { createExportPayload, generatePrompt } from './prompt-engine.js'

test('generates a stable ten-line structured prompt', () => {
  const prompt = generatePrompt({
    styleId: 'cultivation',
    scene: '云海宗门入口',
    uiMode: 'light',
    viewMode: 'image',
  })
  assert.equal(prompt.split('\n').length, 10)
  assert.match(prompt, /东方修仙/)
  assert.match(prompt, /云海宗门入口/)
  assert.match(prompt, /轻量 UI/)
})

test('panorama prompt includes the exact geometric contract', () => {
  const prompt = generatePrompt({
    styleId: 'occult',
    scene: '雾雨街巷',
    uiMode: 'none',
    viewMode: 'panorama',
  })
  assert.match(prompt, /360°×180° 等距柱状投影全景图。/)
  assert.match(prompt, /2:1 宽高比，左右边缘无缝衔接。/)
  assert.match(prompt, /无 HUD、无 UI、无任何可读文字/)
})

test('uploaded references are described without inventing identity claims', () => {
  const prompt = generatePrompt({
    styleId: 'farm',
    scene: '春季农场',
    uiMode: 'full',
    viewMode: 'spatial',
    hasReference: true,
  })
  assert.match(prompt, /上传图片作为场景与构图参考/)
  assert.doesNotMatch(prompt, /保留本人脸/)
})

test('export payload labels spatial preview honestly', () => {
  const payload = createExportPayload({
    sourceName: '本机上传', styleId: 'fantasy', scene: '测试', uiMode: 'none',
    viewMode: 'spatial', prompt: 'prompt',
  })
  assert.match(payload.provenance, /近似深度位移/)
  assert.doesNotMatch(payload.provenance, /Depth Anything/)
})
