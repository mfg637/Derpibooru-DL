INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "my little pony", "copyright");

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="my little pony"), "my little pony");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="my little pony"), "my_little_pony");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="my little pony"), "mlp");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "twilight sparkle", 'characters');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "twilight sparkle");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "twilight_sparkle");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "twi");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "ts");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "rainbow dash", 'characters');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rainbow dash"), "rainbow dash");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rainbow dash"), "rainbow_dash");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rainbow dash"), "rd");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "pinkie pie", 'characters');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="pinkie pie"), "pinkie pie");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="pinkie pie"), "pinkie_pie");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="pinkie pie"), "pp");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "rarity", 'characters');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rarity"), "rarity");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rarity"), "rar");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "fluttershy", 'characters');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="fluttershy"), "fluttershy");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="fluttershy"), "fs");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "applejack", 'characters');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="applejack"), "applejack");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="applejack"), "aj");