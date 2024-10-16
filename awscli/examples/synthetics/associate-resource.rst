**To Associate a canary with a group**

The following ``associate-resource`` example associates a canary with group named `demo_group``. If the command succeeds, no output is returned. ::

    aws synthetics associate-resource \
        --group-identifier demo_group \
        --resource-arn arn:aws:synthetics:us-east-1:123456789012:canary:demo_canary

For more information, see `Synthetic monitoring (canaries) <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html>`__ in the *Amazon CloudWatch User Guide*.