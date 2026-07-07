# Pull Request Template

## Description
Provide a summary of the changes introduced in this PR. Mention any issue numbers this PR resolves.

- **Changes Proposed:**
  - Item 1
  - Item 2
- **Related Issues:** Fixes #

## Category of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Infrastructure/IaC Update
- [ ] CI/CD or DevOps configuration

## How Has This Been Tested?
Please describe the tests that you ran to verify your changes.

- **Automated Test Run:**
  - [ ] `python -m pytest -v` runs and passes successfully.
- **Infrastructure Verification:**
  - [ ] `terraform validate` runs successfully.
  - [ ] Local stack simulated and outputs verified.

## Checklist
- [ ] My code follows the code style guidelines (e.g. PEP 8).
- [ ] I have performed a self-review of my own code.
- [ ] I have commented my code, particularly in hard-to-understand areas.
- [ ] My changes generate no new warnings or console errors.
- [ ] I have added tests that prove my fix is effective or that my feature works.
- [ ] New and existing unit tests pass locally with my changes.
- [ ] Any dependent changes have been merged and published in downstream modules.
