package com.example.warehouse.util;

import com.example.warehouse.dto.Point;

import java.util.ArrayList;
import java.util.List;

public class PathPlanner {
    private PathPlanner() {}

    public static List<Point> manhattanPath(Point start, Point target, Point exit) {
        List<Point> path = new ArrayList<>();
        addSegment(path, start, target);
        addSegment(path, target, exit);
        return path;
    }

    private static void addSegment(List<Point> path, Point from, Point to) {
        int x = from.getX();
        int y = from.getY();
        addIfNew(path, x, y);
        while (x != to.getX()) {
            x += x < to.getX() ? 1 : -1;
            addIfNew(path, x, y);
        }
        while (y != to.getY()) {
            y += y < to.getY() ? 1 : -1;
            addIfNew(path, x, y);
        }
    }

    private static void addIfNew(List<Point> path, int x, int y) {
        if (path.isEmpty() || path.get(path.size() - 1).getX() != x || path.get(path.size() - 1).getY() != y) {
            path.add(new Point(x, y));
        }
    }
}
