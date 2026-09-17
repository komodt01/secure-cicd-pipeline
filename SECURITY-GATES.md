# Security Gates

## Purpose

This document describes how security findings become enforceable delivery decisions in the Secure CI/CD Pipeline.

Security scanning alone does not create a security gate.

A gate exists when a finding is evaluated against policy and the resulting decision can prevent the delivery process from continuing.

The model implemented in this project is:

**Security Finding → Policy Evaluation → Exception Evaluation → Aggregate Decision → Exit Code → CI Enforcement**

---

## Detection Versus Enforcement

A security scanner identifies a technical condition.

Examples include:

- Gitleaks detecting a secret
- Bandit identifying insecure Python code
- pip-audit identifying a vulnerable dependency
- Checkov identifying insecure infrastructure configuration
- Docker Scout identifying a vulnerable container component

Detection answers:

**What security condition exists?**

Enforcement answers:

**Should the pipeline be allowed to continue?**

These are separate architecture decisions.

A scanner can therefore operate as either:

**Detective Control → Report the finding**

or

**Preventive Gate → Report the finding and stop delivery**

depending on how it is integrated into the pipeline.

---

## Centralized Security Gates

The primary enforcement point in this project is the GitHub Actions Continuous Integration pipeline.

Developers may run security tools locally, but local execution is not sufficient as the organizational control because it depends on individual behavior.

Centralized enforcement provides a consistent checkpoint.

The model is:

**Local Security Checks → Fast Feedback**

**Centralized Security Gates → Consistent Enforcement**

---

## Scanner Exit Codes

Command-line security tools communicate execution results through process exit codes.

GitHub Actions interprets a non-zero exit code as a failed workflow step unless explicitly configured otherwise.

Conceptually:

**Exit Code 0 → Continue**

**Non-Zero Exit Code → Fail**

This provides a direct method for turning scanner results into pipeline gates.

---

## Gitleaks Gate

Gitleaks operates as a blocking security control.

When no secret is detected:

**Gitleaks → PASS → Pipeline Continues**

When a secret is detected:

**Gitleaks → Finding → Non-Zero Exit → Pipeline Fails**

The project verified this behavior using a synthetic secret.

The security control remained in place after the test secret was removed.

---

## Bandit Gate

Bandit provides Static Application Security Testing for the Python application.

The project introduced intentionally insecure subprocess behavior and verified that Bandit detected it.

The insecure application code was then remediated.

The desired control relationship is:

**Secure Code → Bandit Passes**

**Applicable Insecure Pattern → Bandit Fails**

The scanner is not removed simply because it discovers a problem.

---

## Dependency Security Gate

pip-audit evaluates Python dependencies against known vulnerability information.

Dependency scanning is separate from source-code scanning because vulnerabilities can exist in third-party software even when internally developed application code is secure.

The gate provides a checkpoint between dependency definition and later delivery stages.

---

## Infrastructure as Code Gate Decision

Checkov is intentionally configured differently from the other controls in this learning implementation.

The workflow uses:

`continue-on-error: true`

This means Checkov findings remain visible while the overall pipeline is permitted to continue.

The current behavior is therefore:

**Finding → Report → Continue**

rather than:

**Finding → Block**

This demonstrates that security detection and security enforcement can be configured independently.

---

## Why `continue-on-error` Is Not a Security Exception

Allowing a pipeline step to continue after an error is not equivalent to formally accepting security risk.

`continue-on-error` changes workflow behavior.

A governed exception should instead include information such as:

- Specific risk
- Business justification
- Risk owner
- Security reviewer
- Approval status
- Expiration
- Remediation plan

This distinction is important because simply making a scanner non-blocking does not create risk governance.

---

## Container Security Gate

The container gate is the most developed policy gate in the project.

Docker Scout performs vulnerability detection against the built container image.

Critical and High findings are exported to SARIF.

The scanner output then becomes input to the Python security decision logic.

The architecture is:

**Container Image → Docker Scout → SARIF Findings → Policy/Exception Gate → CI Decision**

This separates vulnerability detection from organizational risk treatment.

---

## Severity Policy

The container security gate uses the following default policy:

| Severity | Default Decision |
|---|---|
| Critical | BLOCK |
| High | BLOCK |
| Medium | REVIEW |
| Low | ALLOW |

The policy determines the default treatment of a finding.

It does not modify the technical severity assigned to the vulnerability.

---

## Why Scanner Severity and Gate Decision Are Separate

A vulnerability scanner reports information about the technical condition.

The organization determines what that information means to software delivery.

For example:

**High Severity → Default BLOCK**

If an authorized risk process later approves a temporary exception:

**High Severity → Still High → Exception Approved → Deployment Treatment May Change**

The vulnerability itself has not disappeared.

This separation preserves accurate security reporting while still allowing governed business decisions.

---

## Exception Gate

The exception gate evaluates actual Docker Scout findings against `security-exceptions.json`.

An exception must match the vulnerability identifier.

The exception must also be:

**APPROVED**

and:

**Not Expired**

Only then can the exception alter the treatment of that specific finding.

---

## Exception Decision Flow

For each applicable vulnerability:

**Finding Detected**

↓

**Default Security Policy Evaluated**

↓

**Does Matching Exception Exist?**

If no:

**BLOCK**

If yes:

**Is Exception APPROVED?**

If no:

**BLOCK**

If yes:

**Is Exception Unexpired?**

If no:

**BLOCK**

If yes:

**Valid Exception**

The vulnerability remains present, but the accepted risk may proceed.

---

## Exception Scope

An exception applies only to the specific vulnerability represented by the exception record.

It does not:

- Suppress all Docker Scout findings
- Change unrelated vulnerabilities
- Change the underlying vulnerability severity
- Disable the scanner
- Disable the security gate
- Automatically approve future findings

This prevents an exception from becoming a broad security bypass.

---

## Aggregate Gate Decision

The final container security decision must consider all applicable findings.

The gate initializes the overall decision as:

**ALLOW**

Each actual finding is then evaluated.

If an unresolved blocking finding exists, the aggregate state becomes:

**BLOCK**

The final decision remains BLOCK even if another finding has a valid exception.

This creates a fail-safe aggregation model.

---

## Why Aggregation Matters

The project exposed an important implementation risk while developing the gate.

If the final process result were based only on the last exception record evaluated, the pipeline could incorrectly return success even though other blocking vulnerabilities remained.

The gate was corrected so the final process exit status is based on:

`overall_decision`

rather than the decision associated with the final individual record.

This ensures the enforcement result represents the complete security state.

---

## Full Scan Test

The real Docker Scout result contained:

**15 Critical or High vulnerabilities**

One High-severity zlib vulnerability had a valid approved exception.

The remaining findings did not.

The result was:

**15 Findings → 1 Valid Exception → Other Blocking Findings Remain → BLOCK**

The Python process returned:

**Exit Code 1**

GitHub Actions therefore failed the security job.

This is the expected security behavior.

---

## Controlled Exception Test

A controlled test was performed using SARIF containing only the vulnerability covered by the approved exception.

The result was:

**1 Blocking Finding → 1 Valid Approved Exception → No Other Blocking Findings → ALLOW**

The Python process returned:

**Exit Code 0**

This proved that the exception mechanism can permit specifically accepted risk without disabling the security gate.

The complete SARIF results were then restored.

---

## Exception Expiration

Exceptions are intentionally time-bound.

The validation model is:

**Approved + Unexpired → Exception Valid**

**Approved + Expired → Exception Invalid → BLOCK**

**Not Approved → Exception Invalid → BLOCK**

Expiration ensures that temporary risk acceptance must eventually be reconsidered.

An approved exception should not silently become permanent.

---

## CI Enforcement

The final aggregate decision is translated into an exit code.

The implementation follows:

```python
if overall_decision == "BLOCK":
    sys.exit(1)
else:
    sys.exit(0)
```

This creates the enforcement chain:

**Security State → Python Decision → Process Exit Code → GitHub Actions Result**

GitHub Actions does not need to understand the organization's vulnerability policy directly.

It only needs an enforceable success or failure signal from the policy gate.

---

## Security Gate Versus Scanner

The container implementation demonstrates a useful architectural separation.

### Scanner

Docker Scout answers:

**What vulnerabilities exist in this artifact?**

### Policy

`security_policy.py` answers:

**What is the default treatment of this severity?**

### Exception Governance

`security-exceptions.json` answers:

**Has this specific risk been formally accepted?**

### Gate

`exception_check.py` answers:

**After considering the actual findings and valid exceptions, can delivery continue?**

### Enforcement Platform

GitHub Actions answers:

**Should the workflow continue or fail based on the gate result?**

Keeping these responsibilities separate makes the architecture easier to govern and evolve.

---

## Fail-Safe Behavior

The desired gate behavior is conservative:

**Unresolved Blocking Finding → BLOCK**

The architecture should not assume that the existence of any exception means the pipeline is safe to continue.

It should not silently ignore findings it cannot associate with valid risk acceptance.

This supports a fail-safe security posture.

---

## Production Exception Governance

The learning project stores exception records in the repository.

A production environment should provide stronger separation of duties.

A developer should not normally be able to both introduce a security exception and authorize that exception.

Potential controls include:

- Protected repository paths
- CODEOWNERS
- Required security review
- Pull-request approval rules
- External vulnerability-management systems
- Governance, Risk, and Compliance platforms
- Risk-acceptance tickets
- Automated expiration checks
- Audit logging
- Exception ownership
- Compensating-control documentation

The gate should consume approved risk decisions rather than allow unrestricted creation of them.

---

## Future Delivery Gates

The current implementation focuses on source, infrastructure, dependency, and container security.

A broader production pipeline could add additional gates:

**Build**

↓

**Container Security Gate**

↓

**Artifact Repository**

↓

**Test Deployment**

↓

**Dynamic Application Security Testing**

↓

**Security/Quality Gate**

↓

**Required Approval**

↓

**Production**

↓

**Runtime Monitoring**

Other potential controls include Software Bill of Materials generation, artifact signing, signature verification, provenance validation, and deployment authorization.

---

## Security Gate Architecture Summary

The project demonstrates that an effective security gate requires more than installing a scanner.

A complete gate requires:

**Detection**

The security condition must be identified.

**Policy**

The organization must define how the condition should be treated.

**Exception Governance**

Authorized risk acceptance must be controlled and scoped.

**Aggregation**

The complete security state must be evaluated.

**Enforcement**

The decision must be translated into a technical signal that can stop delivery.

The resulting architecture is:

**Finding → Policy → Exception → Aggregate Decision → Exit Code → Enforcement**

That is the difference between simply running security tools in a CI/CD pipeline and designing an enforceable secure software delivery process.
