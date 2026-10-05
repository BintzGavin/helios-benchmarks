import { Browser, LaunchOptions } from 'playwright';
interface LaunchDeps {
    launch: (options: LaunchOptions) => Promise<Browser>;
    install: (browser: string) => void;
}
/**
 * Launches Chromium, installing it first when Playwright has none. A fresh install, a CI
 * runner or a cloud agent sandbox has no browsers, and Playwright's own hint
 * (`npx playwright install`) fetches the latest Playwright's browser build rather than the
 * one this renderer's pinned Playwright expects. So install the matching build, once, and
 * retry. Set HELIOS_SKIP_BROWSER_DOWNLOAD=1 to fail instead.
 */
export declare function launchChromium(options: LaunchOptions, deps?: LaunchDeps): Promise<Browser>;
/** The CLI of the Playwright version this renderer runs on, and the matching install command. */
export declare function playwrightInstallCommand(browser: string): {
    cli: string;
    version: string;
    hint: string;
};
export {};
