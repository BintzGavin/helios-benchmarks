// Command-only fixture uses the requested source range3..302. Payload fixtures
// remain independently labeled ordinal0..299; this does not assert rendered parity.
import {createFixtureScene} from './codec_fixture_scene.mjs';
export function createFixtureSceneForBridge(font) {
 return {...createFixtureScene(font),frameCount:303};
}
