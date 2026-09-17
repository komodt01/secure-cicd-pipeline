# Technical Case Study — Secure CI/CD Security Architecture

## Technical Overview

This project implements a security-focused CI/CD pipeline using GitHub Actions, Python, Docker, Terraform, and multiple security scanning tools.

The objective was to understand and demonstrate how security controls operate across different stages of software delivery and how scanner findings can be translated into enforceable pipeline decisions.

The implemented architecture follows:

**Source → Security Scanning → Build → Artifact Scanning → Policy Evaluation → Exception Evaluation → Aggregate Decision → CI Enforcement**

The project deliberately separates vulnerability detection, security policy, risk exceptions, and pipeline enforcement.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Git / GitHub | Source control and change history |
| GitHub Actions | Continuous Integration orchestration and enforcement |
| Python | Application logic and security policy automation |
| Gitleaks | Secrets scanning |
| Bandit | Static Application Security Testing |
| pip-audit | Python dependency vulnerability scanning |
| Terraform | Infrastructure as Code |
| Checkov | Infrastructure as Code security scanning |
| Docker | Container image creation |
| Docker Scout | Container vulnerability scanning |
| SARIF | Machine-readable security findings |
| JSON | Security exception registry |

---

## Repository Components

The major technical components include:

`app.py`

Demo Python application and initial security-gate learning logic.

`requirements.txt`

Python dependency definitions evaluated by pip-audit.

`infrastructure/main.tf`

Terraform configuration evaluated by Checkov.

`Dockerfile`

Defines the container artifact.

`.github/workflows/security-ci.yml`

Defines the centralized GitHub Actions security workflow.

`security_policy.py`

Defines severity-based security decisions.

`security-exceptions.json`

Stores structured vulnerability exception information.

`exception_check.py`

Evaluates actual Docker Scout findings against approved exceptions and produces the aggregate container security decision.

---

## Pipeline Execution Flow

The implemented pipeline follows this general sequence:

1. Code is committed and pushed to GitHub.
2. GitHub Actions starts the Continuous Integration workflow.
3. Gitleaks scans for exposed secrets.
4. Bandit performs Static Application Security Testing.
5. pip-audit evaluates Python dependencies.
6. Checkov evaluates Terraform configuration.
7. Docker builds the application image.
8. Docker Scout evaluates the built image.
9. Critical and High findings are written to SARIF.
10. Python loads the scanner findings.
11. Python loads the exception registry.
12. Each finding is evaluated for a valid exception.
13. The findings are aggregated into an overall decision.
14. Python returns an exit code.
15. GitHub Actions enforces the result.

The core enforcement path is:

**Finding → Policy → Exception → Aggregate Decision → Exit Code → GitHub Actions**

---

## Secrets Scanning Implementation

Gitleaks is integrated into GitHub Actions using:

```yaml
- name: Scan repository for secrets
  uses: gitleaks/gitleaks-action@v2
```

A synthetic secret was intentionally committed to verify the control.

Gitleaks detected the secret and failed the pipeline.

The test secret was subsequently removed.

This validated that the scanner was not simply installed but was capable of affecting pipeline behavior.

---

## GitHub Push Protection Test

During later workflow development, a real Docker Personal Access Token was accidentally placed directly into the workflow.

GitHub Push Protection detected the credential before the push completed.

The workflow was corrected to use:

```yaml
password: ${{ secrets.DOCKER_TOKEN }}
```

The exposed credential was treated as requiring rotation.

This demonstrated a preventive source-control control operating in addition to the Gitleaks detective control.

---

## Static Application Security Testing

Bandit was installed and used to evaluate `app.py`.

A temporary insecure implementation included subprocess execution using shell behavior.

Bandit identified multiple findings associated with unsafe command execution.

The insecure test code was removed while Bandit remained in the pipeline.

The final architecture uses Bandit to evaluate application source before the container build.

This places source-level security analysis earlier in the delivery process.

---

## Dependency Vulnerability Analysis

pip-audit evaluates the dependencies defined in:

`requirements.txt`

During development, dependency scanning identified a known vulnerability and an available fixed version.

This demonstrated why dependency analysis must remain separate from Static Application Security Testing.

Bandit evaluates code written in the application.

pip-audit evaluates third-party software used by the application.

---

## Infrastructure as Code Security

Checkov evaluates the Terraform configuration under:

`infrastructure/`

The intentionally simple S3 configuration generated multiple security findings.

These included controls associated with areas such as:

- Encryption
- Versioning
- Public-access protection
- Lifecycle configuration
- Replication

For this learning implementation, the workflow uses:

```yaml
- name: Run Infrastructure as Code
  run: checkov -d infrastructure
  continue-on-error: true
```

This intentionally makes the control detective rather than blocking.

The configuration demonstrates that scanner execution and enforcement policy are separate decisions.

---

## Container Build

The application is packaged using Docker.

The base image was updated during the project from Python 3.10 slim to Python 3.12 slim.

The image build creates a new security boundary because the resulting artifact includes components beyond the application source.

The container can include:

- Operating-system packages
- Python runtime
- System libraries
- Application dependencies
- Base-image components

This is why container vulnerability scanning occurs after the build.

---

## Docker Scout Installation

The GitHub Actions runner initially returned an error indicating that `docker scout` was not available.

The runner is ephemeral and did not automatically contain all tools available on the local workstation.

The workflow was therefore updated to install Docker Scout explicitly:

```yaml
- name: Install Docker Scout
  run: |
    curl -sSfL https://raw.githubusercontent.com/docker/scout-cli/main/install.sh | sh -s --
```

This demonstrated the requirement to explicitly define pipeline runtime dependencies.

---

## Docker Authentication

Docker Scout required authentication in the GitHub Actions environment.

The runner could not inherit the developer's local Docker login.

Repository secrets were configured for:

`DOCKER_USERNAME`

and:

`DOCKER_TOKEN`

The workflow authenticates non-interactively:

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_TOKEN }}
```

This introduced machine identity as part of the pipeline architecture.

---

## Container Vulnerability Scanning

The built image is scanned using Docker Scout.

The workflow exports Critical and High findings to SARIF:

```yaml
- name: Scan container image
  run: docker scout cves secure-cicd-demo:latest --only-severity critical,high --format sarif --output scout-results.sarif
```

The resulting file provides structured vulnerability data for the policy gate.

The scanner performs detection.

The Python code performs the organizational decision logic.

---

## Current Container Findings

After updating the base image to Python 3.12 slim, the scan identified:

**15 Critical or High vulnerabilities across 5 packages**

The findings included vulnerabilities associated with packages such as:

- Perl
- glibc
- sqlite3
- pcre2
- zlib

Some findings had available fixed versions.

The zlib High-severity vulnerability used for the exception scenario did not have an available fixed version at the time of testing.

This created the requirement for controlled exception handling.

---

## Security Policy Implementation

The container security policy is defined in:

`security_policy.py`

The implemented logic is:

```python
def evaluate_severity(severity):
    if severity == "Critical":
        return "BLOCK"
    elif severity == "High":
        return "BLOCK"
    elif severity == "Medium":
        return "REVIEW"
    else:
        return "ALLOW"
```

The resulting policy is:

| Severity | Decision |
|---|---|
| Critical | BLOCK |
| High | BLOCK |
| Medium | REVIEW |
| Low | ALLOW |

The policy is intentionally separated from the Docker Scout scanner.

---

## Reusable Python Policy Module

`security_policy.py` also uses:

```python
if __name__ == "__main__":
```

This allows the file to be executed directly for testing while preventing test code from running automatically when the policy function is imported by another Python module.

This supports reuse of the policy logic by the exception gate.

---

## Security Exception Registry

The exception information is stored in:

`security-exceptions.json`

The record includes fields such as:

```json
{
  "vulnerability_id": "CVE-2026-85091",
  "component": "zlib",
  "severity": "High",
  "source": "Docker Scout",
  "reason": "No fixed version currently available",
  "owner": "Application Team",
  "security_reviewer": "Security Architecture",
  "status": "APPROVED",
  "created_date": "2026-09-16",
  "expiration_date": "2026-10-16",
  "remediation_plan": "Upgrade the affected package when a fixed version becomes available"
}
```

The record represents a risk decision rather than vulnerability remediation.

The vulnerability remains present in the scanner results.

---

## Loading Scanner and Exception Data

`exception_check.py` loads both the exception registry and the actual Docker Scout results.

Conceptually:

```python
with open("security-exceptions.json", "r") as file:
    exception_data = json.load(file)

with open("scout-results.sarif", "r") as file:
    scout_data = json.load(file)
```

The scanner findings are extracted from the SARIF structure:

```python
scout_findings = scout_data["runs"][0]["results"]
```

This ensures that the gate evaluates actual current scanner findings rather than only evaluating records that happen to exist in the exception registry.

---

## Exception Lookup

The script creates a list and lookup structure for vulnerability identifiers.

Conceptually:

```python
exception_ids = [
    item["vulnerability_id"]
    for item in exceptions
]
```

and:

```python
exception_lookup = {
    item["vulnerability_id"]: item
    for item in exceptions
}
```

This allows actual scanner findings to be matched to their corresponding exception records.

---

## Expiration Validation

Exception expiration dates are stored as strings in JSON.

Python converts the value using:

```python
expiration = date.fromisoformat(
    matched_exception["expiration_date"]
)
```

The current date is obtained using:

```python
today = date.today()
```

The exception is valid only when it is approved and the current date has not passed the expiration date.

Conceptually:

```python
if matched_exception["status"] == "APPROVED" and today <= expiration:
```

This makes expiration an enforceable security control rather than documentation only.

---

## Aggregate Decision Logic

The gate begins with:

```python
overall_decision = "ALLOW"
```

Every actual Docker Scout finding is evaluated.

If a vulnerability has no valid exception:

```python
overall_decision = "BLOCK"
```

A valid exception does not reset the overall state to ALLOW.

This is important because another unresolved vulnerability may already have caused the container to fail policy.

The aggregate state therefore represents the entire evaluated finding set.

---

## Process Exit Code

The final process result is based on the aggregate decision:

```python
if overall_decision == "BLOCK":
    sys.exit(1)
else:
    sys.exit(0)
```

This implementation was corrected during development after a test showed:

`Overall container security decision: BLOCK`

while the process incorrectly returned exit code 0.

The original behavior was caused by using an individual decision rather than the aggregate state for the final exit.

Correcting this issue ensured that GitHub Actions receives the actual overall security decision.

---

## Exception Gate Workflow Integration

The GitHub Actions workflow executes the policy gate after Docker Scout produces the SARIF file:

```yaml
- name: Evaluate security exceptions
  run: python3 exception_check.py
```

The resulting architecture is:

**Docker Scout**

↓

**SARIF**

↓

**Python Exception Gate**

↓

**Exit Code**

↓

**GitHub Actions**

This creates a clean separation between scanning and enforcement.

---

## Full Security Test

The full Docker Scout scan produced 15 Critical or High findings.

The exception gate identified:

- One vulnerability with a valid exception
- Other vulnerabilities without exceptions

The result was:

```text
Overall container security decision: BLOCK
```

The process returned:

```text
1
```

GitHub Actions therefore failed the workflow as designed.

---

## Controlled Exception Test

To validate the success path without approving unrelated vulnerabilities, a copy of the full SARIF data was preserved.

A temporary test SARIF file was then created containing only:

`CVE-2026-85091`

The exception gate produced:

```text
CVE-2026-85091 VALID EXCEPTION
Overall container security decision: ALLOW
```

The process returned:

```text
0
```

This demonstrated that a valid exception can alter the delivery treatment of the specific accepted risk.

The complete SARIF results were then restored.

---

## Why the Full Pipeline Remains Blocked

The full pipeline is intentionally not forced into a successful state.

The current security state contains unresolved Critical and High vulnerabilities.

The architecture therefore returns:

**BLOCK**

This demonstrates that the security gate is operating according to policy.

A green pipeline is not the objective when the defined security requirements have not been met.

---

## Generated Artifact Handling

`scout-results.sarif` is generated during vulnerability scanning.

It is consumed by the Python gate but does not need to be maintained as application source.

The file is therefore excluded through `.gitignore`.

This keeps runtime scan artifacts separate from source-controlled project files.

---

## Significant Troubleshooting

Several implementation failures provided useful technical lessons.

### Incorrect Workflow Path

The workflow initially referenced:

`exceptions_check.py`

The actual filename was:

`exception_check.py`

The GitHub Actions runner correctly failed because the file did not exist.

### Incorrect Exit Logic

The aggregate decision displayed BLOCK while the process returned success.

The exit logic was corrected to use `overall_decision`.

### Docker Scout Availability

The GitHub runner did not initially contain the required Docker Scout command.

Explicit installation was added.

### Docker Authentication

Local authentication was not available to the ephemeral GitHub Actions runner.

Repository secrets and non-interactive login were added.

### Credential Exposure

A Docker Personal Access Token was accidentally added directly to workflow content.

GitHub Push Protection prevented the push.

The credential was replaced with a repository-secret reference and treated as exposed.

### `.gitignore` Formatting

The generated SARIF filename was accidentally concatenated with another ignore pattern.

Correcting the newline caused Git to properly ignore the runtime scanner output.

These failures were retained as learning outcomes because they demonstrate realistic pipeline implementation and troubleshooting.

---

## Security Design Decisions

### Decision 1 — Scan Before and After Build

Source-oriented controls operate before build.

Container scanning operates after build.

This evaluates both software inputs and the resulting artifact.

### Decision 2 — Separate Scanner From Policy

Docker Scout identifies vulnerabilities.

Python determines organizational treatment.

This reduces coupling between scanner technology and security policy.

### Decision 3 — Use Structured Results

SARIF provides machine-readable findings for automation.

### Decision 4 — Aggregate All Findings

The final gate evaluates all applicable vulnerabilities rather than only exception records.

### Decision 5 — Scope Exceptions

An exception applies only to the identified vulnerability.

### Decision 6 — Enforce Expiration

Approved exceptions become invalid after their expiration date.

### Decision 7 — Preserve Central Enforcement

GitHub Actions provides the authoritative automated checkpoint even when developers use local security tools.

---

## Security Limitations

This project is intentionally scoped as a learning implementation.

Current limitations include:

- Infrastructure as Code findings are non-blocking
- Exceptions are stored in the same repository
- Exception approval is simulated rather than integrated with an enterprise risk system
- No automated remediation workflow exists
- No Software Bill of Materials is currently generated
- Artifact signing is not implemented
- Dynamic Application Security Testing is not implemented
- Production deployment is not implemented
- Runtime monitoring is outside the current implementation

These limitations are documented rather than hidden because they represent architectural boundaries and potential future enhancements.

---

## Production Improvements

A production implementation could introduce:

- Protected branches
- Required pull-request security checks
- CODEOWNERS for security-policy files
- Separation of duties for exception approval
- External vulnerability-management integration
- Governance, Risk, and Compliance integration
- Software Bill of Materials generation
- Artifact signing
- Signature verification
- Build provenance
- Trusted artifact repositories
- Dynamic Application Security Testing
- Deployment security gates
- Centralized logging
- Automated vulnerability reassessment
- Runtime security monitoring
- Automated exception expiration notifications

---

## Technical Outcome

The project successfully demonstrated an end-to-end security decision path from technical finding to Continuous Integration enforcement.

The implemented model is:

**Source Security**

↓

**Dependency Security**

↓

**Infrastructure Security**

↓

**Container Build**

↓

**Artifact Security**

↓

**Structured Findings**

↓

**Security Policy**

↓

**Exception Governance**

↓

**Aggregate Decision**

↓

**Process Exit Code**

↓

**GitHub Actions Enforcement**

The most important technical result was not simply that individual scanners executed successfully.

The project demonstrated how separate security technologies can participate in a unified, policy-driven delivery architecture.

The final implementation can distinguish between:

**No blocking risk → Continue**

**Unresolved blocking risk → Stop**

**Specifically approved and unexpired risk → Permit that finding without bypassing unrelated controls**

This creates a foundation for expanding the project into a broader enterprise secure software delivery architecture.
