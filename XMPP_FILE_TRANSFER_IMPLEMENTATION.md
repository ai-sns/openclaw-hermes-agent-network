# XMPP File Transfer Implementation (XEP-0363)

## Overview
Implemented proper XMPP file transfer using XEP-0363 (HTTP File Upload) protocol instead of sending local file URLs.

## What is XEP-0363?
XEP-0363 is the modern XMPP standard for file transfer. It works by:
1. Client requests an upload slot from XMPP server
2. Server returns PUT URL (for upload) and GET URL (for download)
3. Client uploads file to PUT URL via HTTP
4. Client sends GET URL to recipient via XMPP message
5. Recipient downloads file from GET URL

## Changes Made

### 1. backend/modules/sns/xmpp_client.py

#### Added XEP-0363 Plugin Registration (Line 30)
```python
self.register_plugin('xep_0363')  # HTTP File Upload
```

#### Added File Upload Method (Lines 199-225)
```python
async def upload_and_send_file(self, to_jid: str, file_path: str, filename: str):
    """Upload file via XEP-0363 and send URL to recipient"""
    # Get file info
    file_size = os.path.getsize(file_path)
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    # Upload file using XEP-0363
    with open(file_path, 'rb') as file_handle:
        url = await self['xep_0363'].upload_file(
            filename,
            size=file_size,
            content_type=content_type,
            input_file=file_handle
        )

    # Send URL to recipient
    file_message = f"📎 File: {filename}\n{url}"
    self.send_message_to_jid(to_jid, file_message)

    return url
```

### 2. backend/modules/sns/service.py

#### Updated send_file Method (Lines 170-237)
Changed from:
- Saving file permanently to local server
- Generating local file URL
- Sending local URL to recipient

To:
- Saving file temporarily
- Uploading to XMPP server via XEP-0363
- Sending XMPP server URL to recipient
- Cleaning up temporary file

Key improvements:
```python
# Upload file via XEP-0363 and send to recipient
url = await client.upload_and_send_file(
    to_account,
    str(temp_path),
    file.filename
)

# Clean up temporary file
if temp_path.exists():
    os.remove(temp_path)
```

## How It Works Now

### File Sending Flow:
1. User selects file in frontend
2. Frontend sends file to backend API (`/api/sns/send-file`)
3. Backend saves file temporarily to `uploads/sns_files/`
4. Backend calls `upload_and_send_file()` which:
   - Reads file and gets metadata (size, content type)
   - Calls `self['xep_0363'].upload_file()` to upload to XMPP server
   - XMPP server returns public download URL
   - Sends message with download URL to recipient
5. Backend saves message to database
6. Backend deletes temporary file
7. Recipient receives message with download URL
8. Recipient can download file from XMPP server

### Benefits:
- ✅ Uses standard XMPP protocol (XEP-0363)
- ✅ Files are hosted on XMPP server, not local server
- ✅ Works with any XMPP client that supports XEP-0363
- ✅ No need to expose local server to internet
- ✅ Temporary files are cleaned up automatically

## Server Requirements

The XMPP server must support XEP-0363 (HTTP File Upload). Most modern XMPP servers support this:
- Prosody (with mod_http_upload)
- ejabberd (with mod_http_upload)
- Openfire (with HTTP File Upload plugin)

To verify if your server supports XEP-0363, run:
```bash
python3 test_xmpp_file_upload.py
```

## Testing

1. Start the API server:
```bash
python3 api_server.py
```

2. Open the Electron app and navigate to SNS module

3. Select a contact and try sending a file

4. The file should be uploaded to the XMPP server and the recipient should receive a message with the download URL

## Troubleshooting

### Error: "Server does not support XEP-0363"
- Your XMPP server doesn't have HTTP File Upload enabled
- Contact your XMPP server administrator to enable it
- Or use a different XMPP server that supports XEP-0363

### Error: "File upload failed"
- Check XMPP server logs
- Verify file size is within server limits
- Check network connectivity

### Error: "XMPP client not connected"
- Verify XMPP credentials in database (aichat_cfg table)
- Check XMPP server is accessible
- Review backend logs for connection errors
