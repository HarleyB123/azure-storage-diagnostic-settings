import os
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.subscription import SubscriptionClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.monitor import MonitorManagementClient

TENANT = ""
client_id = os.environ["ARM_CLIENT_ID"]
secret = os.environ["ARM_CLIENT_SECRET"]

CREDENTIALS = ServicePrincipalCredentials(
    client_id=client_id,
    secret=secret,
    tenant=TENANT,
)

sa_metrics = [
    {
        "category": "Transaction",
        "enabled": True,
    }
]

sa_logs = [
    {
        "category": "StorageRead",
        "enabled": True,
    },
    {
        "category": "StorageWrite",
        "enabled": True,
    },
    {
        "category": "StorageDelete",
        "enabled": True,
    },
]

def list_subscriptions():
    client = SubscriptionClient(CREDENTIALS)
    # ignore disabled subscriptions
    subs = [
        sub.subscription_id
        for sub in client.subscriptions.list()
        if sub.state.value == "Enabled"
    ]

    return subs

def list_resource_groups():
    subs = list_subscriptions()
    resource_groups = {}

    for sub in subs:
        resource_group_client = ResourceManagementClient(CREDENTIALS, sub)
        rgs = resource_group_client.resource_groups.list()

        # generate a list of resource groups
        groups = [rg.name for rg in rgs]

        # create a nested dictionary -- {"sub_id": {[rg1, rg2, rg3]}, "sub_id2": {[rg1, rg2, rg3]}}
        resource_groups[sub] = groups
    return resource_groups

def get_az_monitor_diagnostic_setting(rgs):
    log_types = [
        "/blobServices/default",
        "/queueServices/default",
        "/tableServices/default",
        "/fileServices/default",
    ]
    for sub, groups in rgs.items():
        storage_client = StorageManagementClient(CREDENTIALS, sub)
        for rg in groups:
            storage_accounts = storage_client.storage_accounts.list_by_resource_group(rg)
            for account in storage_accounts:
                resource_id = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account.name}"
                client = MonitorManagementClient(CREDENTIALS, sub)
                data = {
                        "workspace_id": "",
                        "metrics": sa_metrics,
                        }
                try:
                    client.diagnostic_settings.create_or_update(resource_id, data, "diagnosticsettingnamehere")
                    print(f"Applying diagnostic settings to {account.name}")
                    for extension in log_types:
                        resource_id = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{account.name}"
                        resource_id = resource_id + extension
                        data = {
                                "workspace_id": "",
                                "metrics": sa_metrics,
                                "logs": sa_logs,
                                }
                        client.diagnostic_settings.create_or_update(resource_id, data, "diagnosticsettingnamehere")
                        print(f"Applying diagnostic settings to {account.name}, type {extension}")
                except:
                    print(f"Error - Couldn't apply all diagnostic settings to {account.name}")

def main():
    rgs = get_resources()
    get_az_monitor_diagnostic_setting(rgs)


if __name__ == "__main__":
    main()
