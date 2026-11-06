<?php
namespace OPNsense\IPv6Holdoff\Api;
class SettingsController extends \OPNsense\Base\ApiMutableModelControllerBase {
    protected static $internalModelName = 'holdoff';
    protected static $internalModelClass = 'OPNsense\IPv6Holdoff\IPv6Holdoff';
}
