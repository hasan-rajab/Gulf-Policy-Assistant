# NEXUS Release Checklist

A NEXUS upgrade is merge-ready only when:

- backend compilation succeeds
- backend/security tests pass
- deterministic evaluation gates pass
- citation-source integrity is 1.0 on the golden demo set
- frontend production build succeeds
- the pull request contains no unresolved correctness regression

Synthetic/demo metrics remain explicitly labelled and are not production guarantees.
