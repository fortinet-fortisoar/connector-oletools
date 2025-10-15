## About the connector

OLEtools is a suite of Python tools used for analyzing Microsoft OLE2 files (also known as Structured Storage, Compound
File Binary Format, or Microsoft Office documents such as .doc, .xls, .ppt, and .msg). It is particularly popular in
digital forensics, malware analysis, and incident response for examining potentially malicious Office documents.
<p>This document provides information about the OLETools Connector, which facilitates automated interactions, with a OLETools server using FortiSOAR&trade; playbooks. Add the OLETools Connector as a step in FortiSOAR&trade; playbooks and perform automated operations with OLETools.</p>

### Version information

Connector Version: 1.0.0

Authored By: Fortinet CSE

Contributor: Daehyeob Kim

Certified: No

## Installing the connector

<p>From FortiSOAR&trade; 5.0.0 onwards, use the <strong>Connector Store</strong> to install the connector. For the detailed procedure to install a connector, click <a href="https://docs.fortinet.com/document/fortisoar/0.0.0/installing-a-connector/1/installing-a-connector" target="_top">here</a>.<br>You can also use the following <code>yum</code> command as a root user to install connectors from an SSH session:</p>
`yum install cyops-connector-oletools`

## Prerequisites to configuring the connector

There are no prerequisites to configuring this connector.

## Minimum Permissions Required

- N/A

## Configuring the connector

For the procedure to configure a connector,
click [here](https://docs.fortinet.com/document/fortisoar/0.0.0/configuring-a-connector/1/configuring-a-connector)

### Configuration parameters

None.
</tbody></table>
## Actions supported by the connector
The following automated operations can be included in playbooks and you can also use the annotations to access operations from FortiSOAR&trade; release 4.10.0 and onwards:
<table border=1><thead><tr><th>Function<br></th><th>Description<br></th><th>Annotation and Category<br></th></tr></thead><tbody><tr><td>Oleid<br></td><td>Scans OLE files for indicators of potential malicious activity (e.g., macros, encryption).<br></td><td>oleid <br/>Investigation<br></td></tr>
<tr><td>Oleobj<br></td><td>Extracts embedded OLE objects (like files or links) from documents.<br></td><td>oleobj <br/>Investigation<br></td></tr>
<tr><td>Olevba<br></td><td>Extracts and analyzes VBA macros from Office documents; detects auto-executable macros and suspicious keywords.<br></td><td>olevba <br/>Investigation<br></td></tr>
</tbody></table>

### operation: Oleid

#### Input parameters

<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>File IRI<br></td><td>Specify the file IRI to activate the oletools analysis on.<br>
</td></tr><tr><td>File Password<br></td><td>If encrypted office files are encountered, try decryption with this password. (if specified dont specify the non_secret_password parameter).<br>
</td></tr></tbody></table>

#### Output

The output contains a non-dictionary value.

### operation: Oleobj

#### Input parameters

<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>File IRI<br></td><td>Specify the file IRI to activate the oletools analysis on.<br>
</td></tr><tr><td>File Password<br></td><td>If encrypted office files are encountered, try decryption with this password. (if specified dont specify the non_secret_password parameter).<br>
</td></tr></tbody></table>

#### Output

The output contains a non-dictionary value.

### operation: Olevba

#### Input parameters

<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>File IRI<br></td><td>Specify the file IRI to activate the oletools analysis on.<br>
</td></tr><tr><td>File Password<br></td><td>If encrypted office files are encountered, try decryption with this password. (if specified dont specify the non_secret_password parameter).<br>
</td></tr><tr><td>Show Decoded Strings<br></td><td>If selected, hex-encoded strings will be displayed with their decoded content. By default, it set as "False".<br>
</td></tr><tr><td>Deobfuscate<br></td><td>If selected, attempt to deobfuscate VBA expressions (slow). By default, it set as "False".<br>
</td></tr></tbody></table>

#### Output

The output contains a non-dictionary value.

## Included playbooks

The `Sample - OLETools - 1.0.0` playbook collection comes bundled with the OLETools connector. These playbooks contain
steps using which you can perform all supported actions. You can see bundled playbooks in the **Automation** > *
*Playbooks** section in FortiSOAR<sup>TM</sup> after importing the OLETools connector.

- Oleid
- Oleobj
- Olevba

**Note**: If you are planning to use any of the sample playbooks in your environment, ensure that you clone those
playbooks and move them to a different collection, since the sample playbook collection gets deleted during connector
upgrade and delete.
