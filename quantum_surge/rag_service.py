import chromadb
from typing import List, Dict, Any

DB_PATH = "./chroma_db"

class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name="security_plus_objectives"
        )
        # Always seed or update database with full list
        self._seed_database()

    def _seed_database(self):
        documents = {
            "security_controls": "Security Controls (Objective 1.1): Technical (firewalls, encryption), Managerial (policies, risk assessment), "
                                 "Operational (training, backups), Physical (guards, locks). Control types include Preventive, "
                                 "Deterrent, Detective, Corrective, Compensating, and Directive.",
            
            "fundamental_concepts": "Fundamental Concepts (Objective 1.2): Confidentiality, Integrity, and Availability (CIA triad). "
                                    "Non-repudiation. AAA framework (Authentication, Authorization, Accounting). Gap analysis. "
                                    "Zero Trust architectures (Control plane: policy engine, policy administrator. Data plane: policy enforcement point). "
                                    "Physical security (bollards, mantraps, lighting, sensors). Deception and disruption (honeypots, honeynets, honeyfiles, honeytokens).",
            
            "change_management": "Change Management (Objective 1.3): Change advisory board, approval processes, ownership, impact analysis. "
                                 "Technical implications (allow lists, restricted activities, downtime, rollbacks, legacy compatibility). "
                                 "Documentation and version control.",
            
            "cryptographic_solutions": "Cryptography (Objective 1.4): Public Key Infrastructure (PKI, public/private keys, key escrow). "
                                       "Encryption levels (full-disk, database, transport/TLS). Symmetric vs asymmetric algorithms. "
                                       "Hashing (SHA), Salting, Digital signatures, key stretching (PBKDF2), obfuscation (steganography), "
                                       "Certificates (CAs, CRLs, OCSP, CSR).",
            
            "threat_actors": "Threat Actors (Objective 2.1): Nation-state, unskilled attackers, hacktivists, insider threats, organized crime, shadow IT. "
                              "Attributes (funding, internal vs external, level of sophistication). Motivations (espionage, financial gain, revenge, disruption).",
            
            "threat_vectors": "Threat Vectors (Objective 2.2): Message-based (phishing, vishing, smishing), client vs agentless software, "
                              "insecure networks (wireless, Bluetooth), open ports, default credentials, supply chain (MSPs, vendors), social engineering.",
            
            "vulnerabilities": "Vulnerabilities (Objective 2.3): Application memory injection, buffer overflow, race conditions (TOC/TOU), OS-based, "
                               "Web-based (SQLi, XSS), hardware end-of-life, virtualization escape, cloud-specific, misconfigurations, mobile sideloading, zero-days.",
            
            "malicious_indicators": "Malicious Indicators (Objective 2.4): Malware attacks (ransomware, Trojans, worms, spyware, rootkits). "
                                    "Physical attacks. Network attacks (DDoS reflected/amplified, DNS poisoning, on-path, replay). "
                                    "Application injection, password brute-force, logging anomalies.",
            
            "mitigation_techniques": "Mitigation (Objective 2.5): Segmentation, ACLs, application allow lists, isolation, patching, encryption, "
                                     "least privilege, configuration enforcement, hardening (HIPS, disabling protocols, default password updates).",
            
            "architecture_models": "Architecture Models (Objective 3.1): Cloud vs on-premises (shared responsibility, serverless, microservices), "
                                   "Infrastructure as Code (IaC), containerization, air-gapped networks, SCADA/ICS IoT devices, RTOS, embedded systems.",
            
            "secure_infrastructure": "Secure Infrastructure (Objective 3.2): Device placement, security zones, jump servers, load balancers, "
                                      "port security (802.1X), Extensible Authentication Protocol (EAP), WAFs, UTMs, NGFWs, VPNs, TLS/IPSec tunneling.",
            
            "protect_data": "Protecting Data (Objective 3.3): Data types (regulated, trade secret, IP). Classifications (confidential, public, private). "
                            "Data states (rest, transit, use). Geolocation. Security methods: masking, tokenization, hashing, encryption.",
            
            "resilience_recovery": "Resilience & Recovery (Objective 3.4): High availability, load balancing, hot/cold/warm sites, geographic dispersion, "
                                   "backups (onsite/offsite, snapshots), journaling, power redundancy (generators, UPS), RTO/RPO objectives.",
            
            "computing_resources": "Secure Resources (Objective 4.1): Baselines, hardening targets (mobile, cloud, workstations, servers, SCADA), "
                                   "MDM profiles, connection methods (cellular, Wi-Fi), WPA3, RADIUS, sandboxing, input validation, code signing.",
            
            "asset_management": "Asset Management (Objective 4.2): Procurement, ownership assignment, monitoring/tracking inventory, "
                                "disposal (decommissioning sanitization, destruction, certification, data retention policies).",
            
            "vulnerability_activities": "Vulnerability Activities (Objective 4.3): Scanning, static/dynamic code analysis (SAST/DAST), "
                                         "OSINT threat feeds, CVSS metrics, CVE reference classifications, verification of remediation.",
            
            "alerting_monitoring": "Alerting & Monitoring (Objective 4.4): Aggregation, SIEM solutions, alert tuning, antivirus tools, SCAP benchmarks, "
                                    "SNMP traps, NetFlow telemetry analysis, vulnerability scanners.",
            
            "enhance_security": "Enhance Security (Objective 4.5): Firewall rulesets, web filters, protocol selection, DNS filtering, "
                                "email authentication (SPF, DKIM, DMARC), file integrity monitoring, DLP, NAC, EDR/XDR endpoints.",
            
            "identity_access": "Identity & Access (Objective 4.6): Provisioning, single sign-on (SSO, LDAP, SAML, OAuth), multifactor authentication (MFA factors), "
                               "password concepts (managers, passwordless), privileged access management (PAM, JIT permissions).",
            
            "automation_orchestration": "Automation (Objective 4.7): Scripting, APIs, SOAR playbooks, benefits (time savings, consistency), "
                                         "technical debt, complexity considerations.",
            
            "incident_response": "Incident Response (Objective 4.8): Preparation, detection, containment, eradication, recovery, lessons learned. "
                                 "Threat hunting, forensics (chain of custody, legal hold, data preservation).",
            
            "data_sources": "Data Sources (Objective 4.9): Firewall logs, endpoint logs, OS-specific logs, packet captures (PCAPs), network metadata.",
            
            "security_governance": "Governance (Objective 5.1): Acceptable Use Policy (AUP), information security policies, SDLC structures, "
                                   "password standards, Change Control, committees, roles (owners, controllers).",
            
            "risk_management": "Risk Management (Objective 5.2): Risk identification, assessment, qualitative vs quantitative analysis (SLE, ALE, ARO), "
                               "risk register, risk appetite, strategies (mitigate, transfer, accept, avoid), RTO/RPO objectives.",
            
            "third_party_risk": "Third-Party Risk (Objective 5.3): Vendor assessments, SLAs, Memorandums of Understanding (MOUs), NDAs, vendor monitoring, "
                                "rules of engagement.",
            
            "security_compliance": "Compliance (Objective 5.4): Compliance reporting, consequences of non-compliance, privacy regulations (GDPR, data sovereignty, privacy rights).",
            
            "audits_assessments": "Audits (Objective 5.5): Internal vs external audits, audit committees, attestation, logical/physical penetration testing (active/passive).",
            
            "awareness_practices": "Awareness (Objective 5.6): Phishing simulations, anomalous behavior recognition, situational awareness training, reporting rules."
        }

        # Clear existing keys to prevent duplicates
        try:
            for key in documents.keys():
                self.collection.delete(ids=[key])
        except Exception:
            pass

        for tid, text in documents.items():
            self.collection.add(
                documents=[text],
                ids=[tid],
                metadatas=[{"topic_id": tid, "source": f"SY0-701 Objective {tid.replace('_', ' ').capitalize()}"}]
            )

    def query_context(self, topic_id: str, limit: int = 1) -> str:
        results = self.collection.query(
            query_texts=[topic_id],
            n_results=limit
        )
        if results and 'documents' in results and len(results['documents']) > 0 and len(results['documents'][0]) > 0:
            return results['documents'][0][0]
        return "CompTIA Security+ exam objectives detail domain constraints for identity, threats, and network infrastructure."
