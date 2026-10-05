import { type JWTVerifyGetKey } from 'jose';
export interface OidcConfig {
    issuer: string;
    audience: string;
    jwksUrl: string;
    subjects: Record<string, string>;
}
/** Map verified workload subjects to tenants. Raw bearer values never enter logs/state. */
export declare function oidcAuthorizer(config: OidcConfig, keySet?: JWTVerifyGetKey): (request: Request) => Promise<string | null>;
