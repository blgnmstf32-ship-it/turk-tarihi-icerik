import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cameraPose} from '../remotion/editorialCamera.ts';
import {collageHTML} from '../media_pilot/editorial_collage.mjs';

test('camera and focus move continuously across all beats in all six tracks', () => {
  for (const track of ['city', 'battle', 'atlas', 'gears', 'barrier', 'cream']) {
    let previous = cameraPose(track, 0);
    const start = previous.position.clone();
    for (let frame = 1; frame <= 270; frame++) {
      const pose = cameraPose(track, frame / 270);
      assert.ok(pose.position.toArray().every(Number.isFinite));
      assert.ok(pose.position.distanceTo(pose.focus) > 5);
      assert.ok(pose.position.distanceTo(previous.position) < .12);
      assert.ok(pose.focus.distanceTo(previous.focus) < .08);
      previous = pose;
    }
    assert.ok(previous.position.distanceTo(start) > 1.5);
    assert.deepEqual(cameraPose(track, -.3).position.toArray(), start.toArray());
    assert.deepEqual(cameraPose(track, 1.4).position.toArray(), previous.position.toArray());
    assert.deepEqual(cameraPose(track, .6).position.toArray(), cameraPose(track, .6).position.toArray());
  }
});

test('HyperFrames composition binds only local assets and escapes title and credit', () => {
  const unsafe = '<img src=https://unsafe.invalid/inject>';
  const history = collageHTML({brand:'tarih', title:unsafe, credit:'<a>Fotoğraf</a>', photo:true, seconds:5});
  assert.match(history, /data-composition-id="paper-board".*data-width="1080".*data-height="1920".*data-duration="5"/);
  assert.match(history, /window\.__timelines\['paper-board'\] = timeline/);
  assert.match(history, /<img src="photo\.jpg"/);
  assert.match(history, /src="gsap\.min\.js"/);
  assert.match(history, /&lt;img src=https:\/\/unsafe\.invalid\/inject&gt;/);
  assert.match(history, /&lt;a&gt;Fotoğraf&lt;\/a&gt;/);
  assert.doesNotMatch(history, /<img src=https:|<a>Fotoğraf/);
  const beauty = collageHTML({brand:'bakim', title:'Ürün etiketi', seconds:5});
  assert.match(beauty, /ETİKET REHBERİ/);
  assert.match(beauty, /plate-pattern/);
  assert.doesNotMatch(beauty, /<img src/);
  assert.throws(() => collageHTML({brand:'bakim', title:'İzin gerektirir', photo:true, seconds:5}));
  assert.throws(() => collageHTML({brand:'bakim', title:'Süre', seconds:Infinity}));
});
