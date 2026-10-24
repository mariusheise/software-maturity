# Security Policy

## Supported versions

Only the latest release and the `main` branch receive security fixes.

## Reporting a vulnerability

Please do not open a public issue. Report privately through GitHub:
[Report a vulnerability](https://github.com/mariusheise/software-maturity/security/advisories/new).

Expect an acknowledgement within 7 days. Fixes are developed in a private
advisory and published together with the advisory once a release is available.

## Verifying releases

Release artifacts carry signed build-provenance and SBOM attestations. Verify
a downloaded artifact with the GitHub CLI:

```sh
gh attestation verify <artifact> --repo mariusheise/software-maturity
gh attestation verify <artifact> --repo mariusheise/software-maturity \
  --predicate-type https://cyclonedx.org/bom
```
