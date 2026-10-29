"""Render CloudFormation JSON with the reviewed bootstrap; no third-party library."""
import json
from pathlib import Path


def ref(name):
    return {"Ref": name}


def attr(name, field):
    return {"Fn::GetAtt": [name, field]}


def template():
    bootstrap = Path(__file__).with_name("bootstrap.sh").read_text()
    # Join rather than Sub: shell $variables are never interpreted as CFN names.
    userdata = {"Fn::Base64": {"Fn::Join": ["", [
        "#!/bin/bash\nexport URBAN_SOURCE_REVISION='", ref("SourceRevision"),
        "'\nexport URBAN_ORIGIN_SECRET='", ref("OriginSecret"), "'\n", bootstrap]]}}
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "UrbanSaarthi synthetic-data demo. Credit-funded EC2/EBS/IPv4; CloudFront pay-as-you-go, not its flat-rate Free plan.",
        "Parameters": {
            "SourceRevision": {"Type": "String", "AllowedPattern": "[0-9a-f]{40}"},
            "OriginSecret": {"Type": "String", "NoEcho": True, "AllowedPattern": "[0-9a-f]{64}"},
            "CloudFrontPrefixList": {"Type": "String", "AllowedPattern": "pl-[0-9a-f]+"},
            "InstanceType": {"Type": "String", "Default": "t3.micro", "AllowedValues": ["t3.micro", "t3.small"]},
            "LatestAmi": {"Type": "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
                          "Default": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"},
        },
        "Resources": {
            "Vpc": {"Type": "AWS::EC2::VPC", "Properties": {
                "CidrBlock": "10.42.0.0/24", "EnableDnsSupport": True, "EnableDnsHostnames": True}},
            "Gateway": {"Type": "AWS::EC2::InternetGateway"},
            "GatewayAttachment": {"Type": "AWS::EC2::VPCGatewayAttachment", "Properties": {
                "VpcId": ref("Vpc"), "InternetGatewayId": ref("Gateway")}},
            "Subnet": {"Type": "AWS::EC2::Subnet", "Properties": {
                "VpcId": ref("Vpc"), "CidrBlock": "10.42.0.0/24"}},
            "RouteTable": {"Type": "AWS::EC2::RouteTable", "Properties": {"VpcId": ref("Vpc")}},
            "PublicRoute": {"Type": "AWS::EC2::Route", "DependsOn": "GatewayAttachment", "Properties": {
                "RouteTableId": ref("RouteTable"), "DestinationCidrBlock": "0.0.0.0/0", "GatewayId": ref("Gateway")}},
            "SubnetRoute": {"Type": "AWS::EC2::SubnetRouteTableAssociation", "Properties": {
                "SubnetId": ref("Subnet"), "RouteTableId": ref("RouteTable")}},
            "WebSecurityGroup": {"Type": "AWS::EC2::SecurityGroup", "Properties": {
                "GroupDescription": "Only CloudFront origin-facing IPv4 HTTP; no SSH or public API port",
                "VpcId": ref("Vpc"), "SecurityGroupIngress": [{
                    "IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
                    "SourcePrefixListId": ref("CloudFrontPrefixList") }]}},
            "InstanceRole": {"Type": "AWS::IAM::Role", "Properties": {
                "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{
                    "Effect": "Allow", "Principal": {"Service": ["ec2.amazonaws.com"]}, "Action": ["sts:AssumeRole"]}]},
                "ManagedPolicyArns": [{"Fn::Sub": "arn:${AWS::Partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"}]}},
            "InstanceProfile": {"Type": "AWS::IAM::InstanceProfile", "Properties": {"Roles": [ref("InstanceRole")]}},
            "Instance": {"Type": "AWS::EC2::Instance", "DependsOn": ["PublicRoute", "SubnetRoute"], "Properties": {
                "ImageId": ref("LatestAmi"), "InstanceType": ref("InstanceType"),
                "IamInstanceProfile": ref("InstanceProfile"), "CreditSpecification": {"CPUCredits": "standard"},
                "MetadataOptions": {"HttpTokens": "required", "HttpPutResponseHopLimit": 1},
                "NetworkInterfaces": [{"DeviceIndex": "0", "SubnetId": ref("Subnet"),
                                       "AssociatePublicIpAddress": False, "GroupSet": [ref("WebSecurityGroup")]}],
                "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {
                    "VolumeSize": 20, "VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}],
                "Tags": [{"Key": "Name", "Value": "urbansaarthi-demo"}, {"Key": "Project", "Value": "UrbanSaarthi"}],
                "UserData": userdata}},
            "Address": {"Type": "AWS::EC2::EIP", "DependsOn": "GatewayAttachment", "Properties": {"Domain": "vpc"}},
            "AddressAssociation": {"Type": "AWS::EC2::EIPAssociation", "Properties": {
                "AllocationId": attr("Address", "AllocationId"), "InstanceId": ref("Instance")}},
            "ForwardHeaders": {"Type": "AWS::CloudFront::OriginRequestPolicy", "Properties": {
                "OriginRequestPolicyConfig": {"Name": {"Fn::Sub": "${AWS::StackName}-api"},
                    "CookiesConfig": {"CookieBehavior": "none"}, "QueryStringsConfig": {"QueryStringBehavior": "all"},
                    "HeadersConfig": {"HeaderBehavior": "whitelist", "Headers": ["Content-Type", "X-Officer-Key", "Idempotency-Key", "Origin", "Access-Control-Request-Method", "Access-Control-Request-Headers"]}}}},
            "Distribution": {"Type": "AWS::CloudFront::Distribution", "DependsOn": "AddressAssociation", "Properties": {
                "DistributionConfig": {"Enabled": True, "HttpVersion": "http2", "IPV6Enabled": True,
                    "Comment": "UrbanSaarthi demo - all responses uncached - pay-as-you-go pricing",
                    "ViewerCertificate": {"CloudFrontDefaultCertificate": True},
                    "Origins": [{"Id": "demo", "DomainName": attr("Instance", "PublicDnsName"),
                        "CustomOriginConfig": {"HTTPPort": 80, "OriginProtocolPolicy": "http-only"},
                        "OriginCustomHeaders": [{"HeaderName": "X-Origin-Verify", "HeaderValue": ref("OriginSecret")}]}],
                    "DefaultCacheBehavior": {"TargetOriginId": "demo", "ViewerProtocolPolicy": "redirect-to-https",
                        "AllowedMethods": ["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"],
                        "CachedMethods": ["GET", "HEAD"], "Compress": True,
                        "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
                        "OriginRequestPolicyId": ref("ForwardHeaders")},
                    "CustomErrorResponses": [{"ErrorCode": code, "ErrorCachingMinTTL": 0}
                                             for code in [400, 403, 404, 405, 414, 416, 500, 501, 502, 503, 504]]}}},
        },
        "Outputs": {
            "WebsiteUrl": {"Value": {"Fn::Join": ["", ["https://", attr("Distribution", "DomainName")]]}},
            "InstanceId": {"Value": ref("Instance")},
            "DistributionId": {"Value": ref("Distribution")},
            "PublicAddress": {"Value": ref("Address")},
            "SourceRevision": {"Value": ref("SourceRevision")},
        },
    }


if __name__ == "__main__":
    print(json.dumps(template(), indent=2))
