// ==UserScript==
// @name        derpibooru_dl_client_script
// @namespace   Violentmonkey Scripts
// @match       https://derpibooru.org/
// @match       https://derpibooru.org/images*
// @match       https://derpibooru.org/search
// @match       https://derpibooru.org/tags/*
// @match       https://twibooru.org/*
// @match       https://ponybooru.org/
// @match       https://ponybooru.org/images*
// @match       https://ponybooru.org/search
// @match       https://ponybooru.org/tags/*
// @match       https://furbooru.org/
// @match       https://furbooru.org/images*
// @match       https://furbooru.org/search
// @match       https://furbooru.org/tags/*
// @match       https://e621.net/popular
// @match       https://e621.net/favorites
// @match       https://e621.net/posts
// @match       https://e621.net/posts/*
// @connect     localhost:5757
// @grant       GM.xmlHttpRequest
// @version     1.3.0
// @author      mfg637
// @description 12.03.2021, 13:25:40
// ==/UserScript==

var url_head = 'http://localhost:5757';

waiting_dl_button = null

function dl_button_click_handler(event){
  console.log(this.data);
  console.log(JSON.stringify(this.data));
  let url = url_head;
  if (document.domain === 'twibooru.org')
    url = url_head + "/twibooru";
  else if (document.domain === "ponybooru.org")
    url = url_head + "/ponybooru";
  else if (document.domain === "e621.net")
    url = url_head + "/e621";
  else if (document.domain === "furbooru.org")
    url = url_head + "/furbooru";
  GM.xmlHttpRequest({
    method: "POST",
    data: JSON.stringify(this.data),
    url: url,
    onload: function(response) {
      if (response.responseText === "OK"){
        event.target.style.backgroundColor = "green";
        event.target.style.color = 'white';
        console.log(response.responseText);
      }else
        alert(response.responseText);
    }
  });
  return false;
}

function button_placer_default(dl_button, image_wrapper){
  dl_button.innerText='dl';
  if (document.domain === "derpibooru.org"){
    dl_button.href = url_head;
    image_wrapper.getElementsByClassName('media-box__header')[0].appendChild(dl_button);
  }else if (document.domain === 'twibooru.org'){
    dl_button.href = url_head + "/twibooru";
    image_wrapper.getElementsByClassName('media-box__header')[0].getElementsByTagName('form')[0].appendChild(dl_button);
  }else if (document.domain === "ponybooru.org"){
    dl_button.href = url_head + "/ponybooru";
    image_wrapper.getElementsByClassName('media-box__header')[0].appendChild(dl_button);
  }else if (document.domain === "furbooru.org"){
    dl_button.href = url_head + "/furbooru";
    image_wrapper.getElementsByClassName('media-box__header')[0].appendChild(dl_button);
  }else if (document.domain === "e621.net"){
    dl_button.href = url_head + "/e621";
    image_wrapper.appendChild(dl_button);
  }
}

function button_placer_show_image(dl_button, unused_arg){
  dl_button.innerText='DDL';
  if (document.domain === "derpibooru.org"){
    dl_button.href = url_head;
  }else if (document.domain === 'twibooru.org'){
    dl_button.href = url_head + "/twibooru";
  }else if (document.domain === "ponybooru.org"){
    dl_button.href = url_head + "/ponybooru";
  }else if (document.domain === "furbooru.org"){
    dl_button.href = url_head + "/furbooru";
  }
  document.getElementsByClassName('image-metabar')[0].appendChild(dl_button);
}

function image_handler(data_wrapper, button_placer, bp_arg=null){
  let raw_data = data_wrapper.dataset, data = {};
  for (let key in raw_data){data[key]=raw_data[key];}
  data.representations=JSON.parse(data.uris);
  delete data.uris;
  let dl_button = document.createElement('a');
  dl_button.data = data;
  dl_button.onclick = dl_button_click_handler;
  dl_button.style.fontWeight = 'Bold';
  button_placer(dl_button, bp_arg);
}


function e621_image_handler(data_wrapper, button_placer, placing_place){
  let raw_data = data_wrapper.dataset, data = {};
  for (let key in raw_data){data[key]=raw_data[key];}
  let dl_button = document.createElement('a');
  dl_button.data = data;
  dl_button.onclick = dl_button_click_handler;
  dl_button.style.fontWeight = 'Bold';
  dl_button.style.marginLeft = "0.5em";
  button_placer(dl_button, placing_place);
}


if  (
      (document.domain === "derpibooru.org") ||
      (document.domain === 'twibooru.org') ||
      (document.domain === "ponybooru.org") ||
      (document.domain === "furbooru.org")
    )
{
  image_wrappers = document.getElementsByClassName('media-box');
  if (image_wrappers.length > 0)
    for (let i in image_wrappers) {
      if (!(image_wrappers[i] instanceof Element)) {
        continue
      }
      data_wrapper = image_wrappers[i].getElementsByClassName('image-container')[0];
      image_handler(data_wrapper, button_placer_default, image_wrappers[i]);
    }
  else {
    image_wrappers = document.getElementsByClassName('image-show-container');
    if (image_wrappers.length > 0) {
      data_wrapper = image_wrappers[0];
      image_handler(data_wrapper, button_placer_show_image);
    }
  }
}else if (document.domain === "e621.net"){
  image_wrappers = document.getElementsByClassName('post-preview');
  if (image_wrappers.length > 0) {
    for (let i in image_wrappers) {
      if (!(image_wrappers[i] instanceof Element)) {
        continue
      }
      e621_image_handler(
          image_wrappers[i],
          button_placer_default,
          image_wrappers[i].getElementsByClassName("post-score")[0]
      );
    }
  }
  image_wrapper = document.getElementById('image-container');
  if (image_wrapper !== null) {
    e621_image_handler(
      image_wrapper,
      button_placer_default,
      document.getElementById("image-extra-controls")
    )
  }
}
