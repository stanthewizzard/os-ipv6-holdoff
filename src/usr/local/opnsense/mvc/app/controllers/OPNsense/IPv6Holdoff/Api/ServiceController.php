<?php
namespace OPNsense\IPv6Holdoff\Api;
class ServiceController extends \OPNsense\Base\ApiControllerBase {
    public function statusAction() {
        return json_decode((new \OPNsense\Core\Backend())->configdRun('ipv6holdoff status'), true) ?? ['phase'=>'stopped'];
    }
    public function reconfigureAction() {
        if (!$this->request->isPost()) return ['status'=>'failed'];
        return ['status'=>trim((new \OPNsense\Core\Backend())->configdRun('ipv6holdoff restart'))];
    }
}
