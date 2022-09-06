/*jslint node: true */
"use strict";

var util = require('util'),
    qlobber = require('..'),
    Qlobber = qlobber.Qlobber;

function QlobberSub (options)
{
    Qlobber.call(this, options);
    this.subscriptionsCount = 0;
}

util.inherits(QlobberSub, Qlobber);

QlobberSub.prototype._initial_value = function (val)
{
    this.subscriptionsCount += 1;

    let r = {
        topic: val.topic,
        clientMap: new Map().set(val.clientId, val.qos),
    };

    r[Symbol.iterator] = function* (topic)
    {
        if (topic === undefined)
        {
            for (let [clientId, qos] of r.clientMap)
            {
                yield { topic: r.topic, clientId, qos };
            }
        }
        else if (r.topic === topic)
        {
            for (let [clientId, qos] of r.clientMap)
            {
                yield { clientId, qos };
            }
        }
    };

    return r;
};

QlobberSub.prototype._add_value = function (existing, val)
{
    var clientMap = existing.clientMap,
        size = clientMap.size;

    clientMap.set(val.clientId, val.qos);

    if (clientMap.size > size)
    {
        this.subscriptionsCount += 1;
    }
};

QlobberSub.prototype._add_values = function (dest, existing, topic)
{
    var clientIdAndQos;
    if (topic === undefined)
    {
        for (clientIdAndQos of existing.clientMap)
        {
            dest.push(
            {
                clientId: clientIdAndQos[0],
                topic: existing.topic,
                qos: clientIdAndQos[1]
            });
        }
    }
    else if (existing.topic === topic)
    {
        for (clientIdAndQos of existing.clientMap)
        {
            dest.push(
            {
                clientId: clientIdAndQos[0],
                qos: clientIdAndQos[1]
            });
        }
    }
};

QlobberSub.prototype._remove_value = function (existing, val)
{
    var clientMap = existing.clientMap,
        size_before = clientMap.size;

    clientMap.delete(val.clientId);

    var size_after = clientMap.size;

    if (size_after < size_before)
    {
        this.subscriptionsCount -= 1;
    }

    return size_after === 0;
};

// Returns whether client is last subscriber to topic
QlobberSub.prototype.test_values = function (existing, val)
{
    var clientMap = existing.clientMap;

    return (existing.topic === val.topic) &&
           (clientMap.size === 1) &&
           clientMap.has(val.clientId);
};

QlobberSub.prototype.match = function (topic, ctx)
{
    return this._match([], 0, topic.split(this._separator), this._trie, ctx);
};

QlobberSub.prototype.clear = function ()
{
    this.subscriptionsCount = 0;
    return Qlobber.prototype.clear.call(this);
};

QlobberSub.set_native = function (qlobber_native)
{
    // wrap_native.js uses 'async *' which isn't available on Node 8
    try
    {
        const wrap_native = require('../lib/wrap_native.js');
        QlobberSub.native = wrap_native(qlobber_native.QlobberSub, QlobberSub);
    }
    catch (ex)
    {
    }

    return module.exports;
};

module.exports = QlobberSub;
