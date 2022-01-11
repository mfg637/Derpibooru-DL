INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "my little pony", "copyright");

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="my little pony"), "my little pony");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="my little pony"), "my_little_pony");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="my little pony"), "mlp");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "twilight sparkle", 'character');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "twilight sparkle");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "twilight_sparkle");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "twi");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="twilight sparkle"), "ts");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "rainbow dash", 'character');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rainbow dash"), "rainbow dash");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rainbow dash"), "rainbow_dash");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rainbow dash"), "rd");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "pinkie pie", 'character');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="pinkie pie"), "pinkie pie");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="pinkie pie"), "pinkie_pie");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="pinkie pie"), "pp");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "rarity", 'character');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rarity"), "rarity");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="rarity"), "rar");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "fluttershy", 'character');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="fluttershy"), "fluttershy");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="fluttershy"), "fs");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "applejack", 'character');

INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="applejack"), "applejack");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="applejack"), "aj");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "friendship is magic", 'content');
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="friendship is magic"), "friendship is magic (season 1)");
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="friendship is magic"), "friendship_is_magic_(s1e1)");

INSERT IGNORE INTO tag (ID, title, category) VALUE (NULL, "equine", 'species');
INSERT IGNORE INTO tag_alias VALUE (NULL, (SELECT ID from tag where tag.title="equine"), "equine");