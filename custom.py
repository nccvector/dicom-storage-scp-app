import socket
import logging

from pydicom.uid import UID
from pynetdicom import evt, AE, build_context, debug_logger, StoragePresentationContexts, AllStoragePresentationContexts
from pynetdicom.sop_class import Verification, CTImageStorage
# from pynetdicom.pdu_primitives import SCP_SCU_RoleSelectionNegotiation
# from pynetdicom.sop_class import CTImageStorage

# GETTING THE HOSTNAME
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

hostname = get_ip()



debug_logger()
LOGGER = logging.getLogger('pynetdicom')

def handle_open(event):
    print("==== OPEN EVENT ====")

    """Print the remote's (host, port) when connected."""
    msg = 'Connected with remote at {}'.format(event.address)
    LOGGER.info(msg)

def handle_accepted(event):
    print("==== ACCEPT EVENT ====")

    """Demonstrate the use of the optional extra parameters"""
    LOGGER.info("Accepted")

# Event handlers
def handle_echo(event):
    print("==== ECHO EVENT ====")

    # Because we used a 2-tuple to bind `handle_echo` we
    #   have no extra parameters
    return 0x0000

def handle_store(event):
    print("==== STORE EVENT ====")

    ds = event.dataset

    # Add the File Meta Information
    ds.file_meta = event.file_meta

    # Save the dataset using the SOP Instance UID as the filename
    ds.save_as(ds.SOPInstanceUID, write_like_original=False)

    # Return a 'Success' status
    return 0x0000

handlers = [
    (evt.EVT_C_ECHO, handle_echo),
    (evt.EVT_C_STORE, handle_store, ['optional', 'parameters']),
    (evt.EVT_CONN_OPEN, handle_open),
    (evt.EVT_ACCEPTED, handle_accepted, ['optional', 'parameters']),
]

ae = AE(ae_title='KPServer')
ae.supported_contexts = AllStoragePresentationContexts
# ae.supported_contexts = StoragePresentationContexts
# ae.add_supported_context(Verification)
# ae.supported_contexts = [build_context(Verification)]
# ae.add_supported_context(CTImageStorage)
# ae.add_supported_context('1.2.840.10008.1.1')
# ae.add_supported_context(UID('1.2.840.10008.5.1.4.1.1.4'))
# ae.add_supported_context(CTImageStorage, scu_role=True, scp_role=False)

print("Starting server  : ", ae.ae_title)
print("Hostname         : ", hostname)
ae.start_server(("169.254.221.80", 104), evt_handlers=handlers)